#!/usr/bin/env python3
"""Network Health Diagnostic Tool

Cross-platform network diagnostics for detecting VPN interference, DNS issues,
routing problems, and connectivity failures. Prevents stealth network bugs from
wasting development time.

Usage as CLI:
    python tools/net_health.py --full
    python tools/net_health.py --brief
    python tools/net_health.py --json

Usage as Agent Tool:
    from tools.net_health import check_network_health
    result = await check_network_health(context)

See /docs_imported/net-health.md for full documentation.
"""

import asyncio
import json
import logging
import platform
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Critical endpoints to test
CRITICAL_ENDPOINTS = {
    "duckduckgo.com": {"ports": [443, 80], "description": "Search API"},
    "google.com": {"ports": [443, 80], "description": "General connectivity"},
    "smtp.gmail.com": {"ports": [465, 587], "description": "Email (Gmail)"},
    "wttr.in": {"ports": [443, 80], "description": "Weather API"},
    "generativelanguage.googleapis.com": {"ports": [443], "description": "Gemini API"},
}

# Known VPN adapter patterns
VPN_PATTERNS = [
    "radmin", "hamachi", "zerotier", "tailscale", "wireguard",
    "openvpn", "nordvpn", "expressvpn", "tunnel", "tap", "tun",
    "vpn", "virtual", "wan miniport"
]


@dataclass
class NetworkAdapter:
    """Represents a network adapter."""
    name: str
    is_up: bool
    is_vpn: bool
    addresses: List[str] = field(default_factory=list)
    gateway: Optional[str] = None
    metric: Optional[int] = None


@dataclass
class DNSConfig:
    """DNS configuration."""
    servers: List[str] = field(default_factory=list)
    source: str = "unknown"


@dataclass
class EndpointTest:
    """Results of testing an endpoint."""
    hostname: str
    description: str
    resolved: bool
    ip_address: Optional[str] = None
    ports_tested: Dict[int, bool] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class NetworkHealth:
    """Complete network health report."""
    os_platform: str
    adapters: List[NetworkAdapter] = field(default_factory=list)
    default_adapter: Optional[str] = None
    default_gateway: Optional[str] = None
    dns_config: Optional[DNSConfig] = None
    proxy_detected: bool = False
    vpn_active: bool = False
    vpn_adapters: List[str] = field(default_factory=list)
    endpoint_tests: List[EndpointTest] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class NetworkHealthChecker:
    """Cross-platform network health diagnostics."""

    def __init__(self):
        self.platform = platform.system()
        logger.info(f"NetworkHealthChecker initialized for {self.platform}")

    async def check_full_health(self) -> NetworkHealth:
        """Perform complete network health check."""
        logger.info("Starting full network health check...")
        
        health = NetworkHealth(os_platform=self.platform)
        
        try:
            # Get adapters
            health.adapters = await self._get_adapters()
            health.default_adapter, health.default_gateway = await self._get_default_route()
            
            # Check for VPN
            health.vpn_adapters = [a.name for a in health.adapters if a.is_vpn and a.is_up]
            health.vpn_active = len(health.vpn_adapters) > 0
            
            # Get DNS config
            health.dns_config = await self._get_dns_config()
            
            # Check proxy
            health.proxy_detected = self._check_proxy()
            
            # Test endpoints
            health.endpoint_tests = await self._test_endpoints()
            
            # Analyze and generate issues/suggestions
            self._analyze_health(health)
            
            logger.info("Network health check completed")
            
        except Exception as e:
            logger.error(f"Error during health check: {e}", exc_info=True)
            health.issues.append(f"Health check failed: {str(e)}")
        
        return health

    async def _get_adapters(self) -> List[NetworkAdapter]:
        """Get all network adapters (cross-platform)."""
        logger.debug(f"Getting adapters for {self.platform}")
        
        if self.platform == "Windows":
            return await self._get_adapters_windows()
        elif self.platform == "Linux":
            return await self._get_adapters_linux()
        elif self.platform == "Darwin":
            return await self._get_adapters_macos()
        else:
            logger.warning(f"Unsupported platform: {self.platform}")
            return []

    async def _get_adapters_windows(self) -> List[NetworkAdapter]:
        """Get Windows network adapters using ipconfig and Get-NetAdapter."""
        adapters = []
        
        try:
            # Use PowerShell to get adapter details with metrics
            cmd = [
                "powershell", "-Command",
                "Get-NetAdapter | Select-Object Name,Status,InterfaceMetric | ConvertTo-Json"
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                adapter_data = json.loads(stdout.decode('utf-8', errors='ignore'))
                if not isinstance(adapter_data, list):
                    adapter_data = [adapter_data]
                
                for item in adapter_data:
                    name = item.get("Name", "")
                    status = item.get("Status", "")
                    metric = item.get("InterfaceMetric")
                    
                    is_vpn = any(pattern in name.lower() for pattern in VPN_PATTERNS)
                    is_up = status.lower() == "up"
                    
                    adapter = NetworkAdapter(
                        name=name,
                        is_up=is_up,
                        is_vpn=is_vpn,
                        metric=metric
                    )
                    adapters.append(adapter)
                    
                    if is_vpn:
                        logger.warning(f"VPN adapter detected: {name} (status: {status})")
            
        except Exception as e:
            logger.error(f"Error getting Windows adapters: {e}")
            # Fallback to basic method
            adapters = await self._get_adapters_fallback()
        
        return adapters

    async def _get_adapters_linux(self) -> List[NetworkAdapter]:
        """Get Linux network adapters using ip link."""
        adapters = []
        
        try:
            result = await asyncio.create_subprocess_exec(
                "ip", "link", "show",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                output = stdout.decode('utf-8', errors='ignore')
                
                for line in output.split('\n'):
                    if ': ' in line and not line.startswith(' '):
                        parts = line.split(': ')
                        if len(parts) >= 2:
                            name = parts[1].split('@')[0]
                            is_up = 'UP' in line.upper()
                            is_vpn = any(pattern in name.lower() for pattern in VPN_PATTERNS)
                            
                            adapter = NetworkAdapter(
                                name=name,
                                is_up=is_up,
                                is_vpn=is_vpn
                            )
                            adapters.append(adapter)
                            
                            if is_vpn:
                                logger.warning(f"VPN adapter detected: {name}")
        
        except Exception as e:
            logger.error(f"Error getting Linux adapters: {e}")
            adapters = await self._get_adapters_fallback()
        
        return adapters

    async def _get_adapters_macos(self) -> List[NetworkAdapter]:
        """Get macOS network adapters using networksetup."""
        adapters = []
        
        try:
            result = await asyncio.create_subprocess_exec(
                "networksetup", "-listallhardwareports",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                output = stdout.decode('utf-8', errors='ignore')
                current_name = None
                
                for line in output.split('\n'):
                    if line.startswith("Hardware Port:"):
                        current_name = line.split(": ", 1)[1].strip()
                    elif line.startswith("Device:") and current_name:
                        device = line.split(": ", 1)[1].strip()
                        is_vpn = any(pattern in current_name.lower() for pattern in VPN_PATTERNS)
                        
                        adapter = NetworkAdapter(
                            name=current_name,
                            is_up=True,  # Would need additional check
                            is_vpn=is_vpn
                        )
                        adapters.append(adapter)
                        
                        if is_vpn:
                            logger.warning(f"VPN adapter detected: {current_name}")
                        
                        current_name = None
        
        except Exception as e:
            logger.error(f"Error getting macOS adapters: {e}")
            adapters = await self._get_adapters_fallback()
        
        return adapters

    async def _get_adapters_fallback(self) -> List[NetworkAdapter]:
        """Fallback method using socket library."""
        adapters = []
        
        try:
            # At minimum, detect if we can get any network info
            hostname = socket.gethostname()
            adapter = NetworkAdapter(
                name=hostname,
                is_up=True,
                is_vpn=False
            )
            adapters.append(adapter)
        except Exception as e:
            logger.error(f"Fallback adapter detection failed: {e}")
        
        return adapters

    async def _get_default_route(self) -> Tuple[Optional[str], Optional[str]]:
        """Get default network adapter and gateway."""
        logger.debug("Getting default route")
        
        try:
            if self.platform == "Windows":
                return await self._get_default_route_windows()
            elif self.platform == "Linux":
                return await self._get_default_route_linux()
            elif self.platform == "Darwin":
                return await self._get_default_route_macos()
        except Exception as e:
            logger.error(f"Error getting default route: {e}")
        
        return None, None

    async def _get_default_route_windows(self) -> Tuple[Optional[str], Optional[str]]:
        """Get Windows default route using route print."""
        try:
            result = await asyncio.create_subprocess_exec(
                "route", "print", "0.0.0.0",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                output = stdout.decode('utf-8', errors='ignore')
                
                for line in output.split('\n'):
                    if '0.0.0.0' in line and 'On-link' not in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            gateway = parts[2]
                            if gateway != '0.0.0.0' and gateway != 'On-link':
                                logger.info(f"Default gateway found: {gateway}")
                                return "Default", gateway
        except Exception as e:
            logger.error(f"Error getting Windows default route: {e}")
        
        return None, None

    async def _get_default_route_linux(self) -> Tuple[Optional[str], Optional[str]]:
        """Get Linux default route using ip route."""
        try:
            result = await asyncio.create_subprocess_exec(
                "ip", "route", "show", "default",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                output = stdout.decode('utf-8', errors='ignore').strip()
                
                # Parse: default via 192.168.1.1 dev eth0 ...
                parts = output.split()
                gateway = None
                adapter = None
                
                if 'via' in parts:
                    gateway = parts[parts.index('via') + 1]
                if 'dev' in parts:
                    adapter = parts[parts.index('dev') + 1]
                
                logger.info(f"Default route: adapter={adapter}, gateway={gateway}")
                return adapter, gateway
        except Exception as e:
            logger.error(f"Error getting Linux default route: {e}")
        
        return None, None

    async def _get_default_route_macos(self) -> Tuple[Optional[str], Optional[str]]:
        """Get macOS default route using netstat."""
        try:
            result = await asyncio.create_subprocess_exec(
                "netstat", "-rn",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                output = stdout.decode('utf-8', errors='ignore')
                
                for line in output.split('\n'):
                    if line.startswith('default'):
                        parts = line.split()
                        if len(parts) >= 4:
                            gateway = parts[1]
                            adapter = parts[3]
                            logger.info(f"Default route: adapter={adapter}, gateway={gateway}")
                            return adapter, gateway
        except Exception as e:
            logger.error(f"Error getting macOS default route: {e}")
        
        return None, None

    async def _get_dns_config(self) -> DNSConfig:
        """Get DNS server configuration."""
        logger.debug("Getting DNS configuration")
        
        try:
            if self.platform == "Windows":
                return await self._get_dns_windows()
            elif self.platform == "Linux":
                return await self._get_dns_linux()
            elif self.platform == "Darwin":
                return await self._get_dns_macos()
        except Exception as e:
            logger.error(f"Error getting DNS config: {e}")
        
        return DNSConfig(servers=[], source="error")

    async def _get_dns_windows(self) -> DNSConfig:
        """Get Windows DNS servers from PowerShell."""
        try:
            cmd = [
                "powershell", "-Command",
                "Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object {$_.ServerAddresses} | Select-Object -ExpandProperty ServerAddresses"
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                servers = [s.strip() for s in stdout.decode('utf-8', errors='ignore').split('\n') if s.strip()]
                logger.info(f"DNS servers found: {servers}")
                return DNSConfig(servers=servers, source="PowerShell")
        except Exception as e:
            logger.error(f"Error getting Windows DNS: {e}")
        
        return DNSConfig(servers=[], source="windows_error")

    async def _get_dns_linux(self) -> DNSConfig:
        """Get Linux DNS from /etc/resolv.conf."""
        try:
            resolv_path = Path("/etc/resolv.conf")
            if resolv_path.exists():
                content = resolv_path.read_text()
                servers = []
                
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('nameserver'):
                        parts = line.split()
                        if len(parts) >= 2:
                            servers.append(parts[1])
                
                logger.info(f"DNS servers from /etc/resolv.conf: {servers}")
                return DNSConfig(servers=servers, source="/etc/resolv.conf")
        except Exception as e:
            logger.error(f"Error reading /etc/resolv.conf: {e}")
        
        return DNSConfig(servers=[], source="linux_error")

    async def _get_dns_macos(self) -> DNSConfig:
        """Get macOS DNS using scutil."""
        try:
            result = await asyncio.create_subprocess_exec(
                "scutil", "--dns",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                output = stdout.decode('utf-8', errors='ignore')
                servers = []
                
                for line in output.split('\n'):
                    line = line.strip()
                    if line.startswith('nameserver['):
                        parts = line.split(':')
                        if len(parts) >= 2:
                            servers.append(parts[1].strip())
                
                # Remove duplicates while preserving order
                servers = list(dict.fromkeys(servers))
                logger.info(f"DNS servers from scutil: {servers}")
                return DNSConfig(servers=servers, source="scutil")
        except Exception as e:
            logger.error(f"Error getting macOS DNS: {e}")
        
        return DNSConfig(servers=[], source="macos_error")

    def _check_proxy(self) -> bool:
        """Check if proxy is configured."""
        try:
            import os
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
            
            for var in proxy_vars:
                if os.environ.get(var):
                    logger.warning(f"Proxy detected: {var}={os.environ.get(var)}")
                    return True
        except Exception as e:
            logger.error(f"Error checking proxy: {e}")
        
        return False

    async def _test_endpoints(self) -> List[EndpointTest]:
        """Test connectivity to critical endpoints."""
        logger.info("Testing critical endpoints...")
        results = []
        
        tasks = []
        for hostname, config in CRITICAL_ENDPOINTS.items():
            task = self._test_single_endpoint(hostname, config)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        endpoint_tests = [r for r in results if isinstance(r, EndpointTest)]
        
        return endpoint_tests

    async def _test_single_endpoint(self, hostname: str, config: Dict) -> EndpointTest:
        """Test a single endpoint (DNS + TCP connectivity)."""
        test = EndpointTest(
            hostname=hostname,
            description=config['description'],
            resolved=False
        )
        
        try:
            # DNS resolution
            logger.debug(f"Resolving {hostname}...")
            loop = asyncio.get_event_loop()
            ip_address = await asyncio.wait_for(
                loop.run_in_executor(None, socket.gethostbyname, hostname),
                timeout=5.0
            )
            
            test.resolved = True
            test.ip_address = ip_address
            logger.info(f"{hostname} resolved to {ip_address}")
            
            # Test TCP ports
            for port in config['ports']:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3.0)
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, sock.connect_ex, (ip_address, port)),
                        timeout=4.0
                    )
                    sock.close()
                    
                    test.ports_tested[port] = (result == 0)
                    if result == 0:
                        logger.info(f"{hostname}:{port} - OPEN")
                    else:
                        logger.warning(f"{hostname}:{port} - CLOSED/FILTERED")
                
                except asyncio.TimeoutError:
                    test.ports_tested[port] = False
                    logger.warning(f"{hostname}:{port} - TIMEOUT")
                except Exception as e:
                    test.ports_tested[port] = False
                    logger.error(f"{hostname}:{port} - ERROR: {e}")
        
        except asyncio.TimeoutError:
            test.error = "DNS resolution timeout"
            logger.error(f"{hostname} - DNS timeout")
        except socket.gaierror as e:
            test.error = f"DNS resolution failed: {e}"
            logger.error(f"{hostname} - DNS failed: {e}")
        except Exception as e:
            test.error = str(e)
            logger.error(f"{hostname} - ERROR: {e}")
        
        return test

    def _analyze_health(self, health: NetworkHealth):
        """Analyze health data and generate issues/suggestions."""
        
        # Check VPN
        if health.vpn_active:
            health.issues.append(f"VPN adapter(s) active: {', '.join(health.vpn_adapters)}")
            health.suggestions.append(
                "VPN adapters can cause routing issues. "
                "Disable VPN if experiencing connectivity problems."
            )
        
        # Check DNS
        if health.dns_config and not health.dns_config.servers:
            health.issues.append("No DNS servers detected")
            health.suggestions.append("Configure DNS servers (e.g., 8.8.8.8, 1.1.1.1)")
        elif health.dns_config and '1.1.1.1' in health.dns_config.servers:
            health.issues.append("Using Cloudflare DNS (1.1.1.1)")
            health.suggestions.append(
                "Some services may have issues with Cloudflare DNS. "
                "Try Google DNS (8.8.8.8) if problems persist."
            )
        
        # Check endpoint failures
        failed_dns = []
        failed_ports = []
        
        for test in health.endpoint_tests:
            if not test.resolved:
                failed_dns.append(test.hostname)
            else:
                for port, success in test.ports_tested.items():
                    if not success:
                        failed_ports.append(f"{test.hostname}:{port}")
        
        if failed_dns:
            health.issues.append(f"DNS resolution failed: {', '.join(failed_dns)}")
            health.suggestions.append(
                "DNS resolution failures indicate network or DNS server issues. "
                "Check DNS configuration and network connectivity."
            )
        
        if failed_ports:
            health.issues.append(f"Port connectivity failed: {', '.join(failed_ports[:5])}")
            health.suggestions.append(
                "Port connectivity failures may indicate firewall blocking or routing issues."
            )
        
        # Check proxy
        if health.proxy_detected:
            health.issues.append("HTTP/HTTPS proxy detected in environment")
            health.suggestions.append("Proxies can interfere with direct connections. Verify proxy settings.")
        
        # Check for no default gateway
        if not health.default_gateway:
            health.issues.append("No default gateway detected")
            health.suggestions.append("Network may not be properly configured. Check adapter settings.")


def format_health_report(health: NetworkHealth, mode: str = "full") -> str:
    """Format health report as text."""
    
    lines = []
    lines.append("=" * 60)
    lines.append("NETWORK HEALTH REPORT")
    lines.append("=" * 60)
    lines.append(f"Platform: {health.os_platform}")
    lines.append("")
    
    # Adapters
    if mode == "full":
        lines.append("Network Adapters:")
        for adapter in health.adapters:
            status = "UP" if adapter.is_up else "DOWN"
            vpn_flag = " [VPN]" if adapter.is_vpn else ""
            metric = f" (metric: {adapter.metric})" if adapter.metric else ""
            lines.append(f"  - {adapter.name}: {status}{vpn_flag}{metric}")
        lines.append("")
    
    # Default route
    if health.default_adapter or health.default_gateway:
        lines.append(f"Default Adapter: {health.default_adapter or 'N/A'}")
        lines.append(f"Default Gateway: {health.default_gateway or 'N/A'}")
        lines.append("")
    
    # DNS
    if health.dns_config:
        lines.append(f"DNS Servers ({health.dns_config.source}):")
        for server in health.dns_config.servers:
            lines.append(f"  - {server}")
        lines.append("")
    
    # Proxy
    if health.proxy_detected:
        lines.append("⚠️  Proxy: DETECTED")
        lines.append("")
    
    # VPN Status
    if health.vpn_active:
        lines.append("⚠️  VPN Status: ACTIVE")
        lines.append(f"VPN Adapters: {', '.join(health.vpn_adapters)}")
        lines.append("")
    else:
        lines.append("✓ VPN Status: INACTIVE")
        lines.append("")
    
    # Endpoint tests
    if mode in ["full", "brief"]:
        lines.append("Endpoint Connectivity:")
        for test in health.endpoint_tests:
            if test.resolved:
                ip_str = f"→ {test.ip_address}" if test.ip_address else ""
                ports_ok = sum(1 for v in test.ports_tested.values() if v)
                ports_total = len(test.ports_tested)
                
                if ports_ok == ports_total:
                    status = "✓"
                elif ports_ok > 0:
                    status = "⚠️"
                else:
                    status = "✗"
                
                lines.append(f"  {status} {test.hostname} {ip_str}")
                
                if mode == "full":
                    for port, success in test.ports_tested.items():
                        port_status = "OPEN" if success else "CLOSED"
                        lines.append(f"      Port {port}: {port_status}")
            else:
                lines.append(f"  ✗ {test.hostname} - {test.error or 'DNS FAILED'}")
        lines.append("")
    
    # Issues
    if health.issues:
        lines.append("⚠️  ISSUES DETECTED:")
        for issue in health.issues:
            lines.append(f"  • {issue}")
        lines.append("")
    
    # Suggestions
    if health.suggestions:
        lines.append("💡 SUGGESTIONS:")
        for suggestion in health.suggestions:
            lines.append(f"  • {suggestion}")
        lines.append("")
    
    # Summary
    if not health.issues:
        lines.append("✓ Network health: GOOD")
    elif len(health.issues) <= 2:
        lines.append("⚠️  Network health: FAIR (minor issues)")
    else:
        lines.append("✗ Network health: POOR (multiple issues)")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def format_health_brief(health: NetworkHealth) -> str:
    """Format brief health report (for voice/agent)."""
    
    parts = []
    
    # Default adapter and gateway
    if health.default_adapter:
        parts.append(f"Default network is {health.default_adapter}")
    
    if health.default_gateway:
        parts.append(f"gateway {health.default_gateway}")
    
    # DNS
    if health.dns_config and health.dns_config.servers:
        dns_str = ", ".join(health.dns_config.servers[:2])
        parts.append(f"DNS: {dns_str}")
    
    # VPN status
    if health.vpn_active:
        parts.append(f"⚠️ VPN ACTIVE on {', '.join(health.vpn_adapters)}")
    else:
        parts.append("VPN inactive")
    
    # Endpoint summary
    total_tests = len(health.endpoint_tests)
    resolved = sum(1 for t in health.endpoint_tests if t.resolved)
    
    if resolved == total_tests:
        parts.append(f"All {total_tests} critical endpoints reachable")
    elif resolved > 0:
        parts.append(f"{resolved}/{total_tests} endpoints reachable")
    else:
        parts.append("⚠️ NO endpoints reachable")
    
    # Issues summary
    if health.issues:
        parts.append(f"⚠️ {len(health.issues)} issue(s) detected")
    
    return ". ".join(parts) + "."


# ============================================================================
# Agent Tool Interface
# ============================================================================

try:
    from livekit.agents import function_tool, RunContext
    
    @function_tool
    async def check_network_health(context: RunContext) -> str:  # type: ignore
        """Check network health and diagnose connectivity issues.
        
        This tool detects VPN interference, DNS problems, routing issues,
        and tests connectivity to critical API endpoints. Use this before
        reporting external API failures to determine if the issue is network-related.
        
        Returns:
            Brief network health report with status and any issues found.
        """
        try:
            checker = NetworkHealthChecker()
            health = await checker.check_full_health()
            
            # Return brief summary for voice
            result = format_health_brief(health)
            
            # Add specific troubleshooting if issues found
            if health.issues:
                result += "\n\nIssues: " + "; ".join(health.issues[:3])
            
            if health.suggestions:
                result += "\n\nSuggestion: " + health.suggestions[0]
            
            logging.info(f"Network health check completed: {len(health.issues)} issues")
            return result
            
        except Exception as e:
            error_msg = f"error: network health check failed: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return error_msg

except ImportError:
    # Running standalone, not as agent tool
    logger.debug("Running in standalone mode (livekit not available)")


# ============================================================================
# CLI Interface
# ============================================================================

async def main_cli():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Network Health Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/net_health.py --full          # Full detailed report
  python tools/net_health.py --brief         # Brief summary
  python tools/net_health.py --json          # JSON output
  
This tool helps diagnose VPN interference, DNS issues, and connectivity problems.
        """
    )
    
    parser.add_argument(
        "--full", action="store_true",
        help="Full detailed report (default)"
    )
    parser.add_argument(
        "--brief", action="store_true",
        help="Brief summary report"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Determine mode
    if args.brief:
        mode = "brief"
    elif args.json:
        mode = "json"
    else:
        mode = "full"
    
    # Run health check
    checker = NetworkHealthChecker()
    health = await checker.check_full_health()
    
    # Output results
    if mode == "json":
        # Convert to dict for JSON serialization
        output = {
            "os_platform": health.os_platform,
            "default_adapter": health.default_adapter,
            "default_gateway": health.default_gateway,
            "dns_servers": health.dns_config.servers if health.dns_config else [],
            "vpn_active": health.vpn_active,
            "vpn_adapters": health.vpn_adapters,
            "proxy_detected": health.proxy_detected,
            "adapters": [
                {
                    "name": a.name,
                    "is_up": a.is_up,
                    "is_vpn": a.is_vpn,
                    "metric": a.metric
                } for a in health.adapters
            ],
            "endpoint_tests": [
                {
                    "hostname": t.hostname,
                    "description": t.description,
                    "resolved": t.resolved,
                    "ip_address": t.ip_address,
                    "ports": {str(k): v for k, v in t.ports_tested.items()},
                    "error": t.error
                } for t in health.endpoint_tests
            ],
            "issues": health.issues,
            "suggestions": health.suggestions
        }
        print(json.dumps(output, indent=2))
    
    elif mode == "brief":
        print(format_health_brief(health))
    
    else:  # full
        print(format_health_report(health, mode="full"))
    
    # Exit code based on health
    if health.issues:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main_cli())
