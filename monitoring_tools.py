#!/usr/bin/env python3
"""
Production Monitoring & Load Testing Tools for Grapnel Backend
Includes performance monitoring, load testing, and system health checks
"""

import asyncio
import aiohttp
import json
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import argparse
import csv
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import psutil
import sys

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    endpoint: str
    method: str
    response_time: float
    status_code: int
    success: bool
    timestamp: datetime
    payload_size: int = 0
    response_size: int = 0

class SystemMonitor:
    """System performance monitoring"""
    
    def __init__(self):
        self.metrics = []
        self.start_time = datetime.now()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "network": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
            "timestamp": datetime.now().isoformat()
        }
    
    def log_metric(self, metric: PerformanceMetrics):
        """Log performance metric"""
        self.metrics.append(metric)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics:
            return {"error": "No metrics collected"}
        
        response_times = [m.response_time for m in self.metrics]
        success_count = sum(1 for m in self.metrics if m.success)
        
        return {
            "total_requests": len(self.metrics),
            "successful_requests": success_count,
            "success_rate": (success_count / len(self.metrics)) * 100,
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "avg": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "p95": self._percentile(response_times, 95),
                "p99": self._percentile(response_times, 99)
            },
            "error_distribution": self._get_error_distribution(),
            "duration": (datetime.now() - self.start_time).total_seconds()
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        return statistics.quantiles(data, n=100)[percentile-1] if len(data) > 1 else data[0]
    
    def _get_error_distribution(self) -> Dict[int, int]:
        """Get distribution of HTTP status codes"""
        distribution = {}
        for metric in self.metrics:
            code = metric.status_code
            distribution[code] = distribution.get(code, 0) + 1
        return distribution
    
    def export_to_csv(self, filename: str):
        """Export metrics to CSV file"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'endpoint', 'method', 'response_time', 
                         'status_code', 'success', 'payload_size', 'response_size']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for metric in self.metrics:
                writer.writerow({
                    'timestamp': metric.timestamp.isoformat(),
                    'endpoint': metric.endpoint,
                    'method': metric.method,
                    'response_time': metric.response_time,
                    'status_code': metric.status_code,
                    'success': metric.success,
                    'payload_size': metric.payload_size,
                    'response_size': metric.response_size
                })

class LoadTester:
    """Load testing functionality"""
    
    def __init__(self, base_url: str, concurrent_users: int = 10):
        self.base_url = base_url.rstrip('/')
        self.concurrent_users = concurrent_users
        self.monitor = SystemMonitor()
        self.session = None
    
    async def setup_session(self):
        """Initialize HTTP session with connection pooling"""
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per host connection limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "GrapnelLoadTester/1.0"}
        )
    
    async def cleanup_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: dict = None) -> PerformanceMetrics:
        """Make HTTP request and collect metrics"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        timestamp = datetime.now()
        payload_size = len(json.dumps(data)) if data else 0
        
        try:
            headers = {"Content-Type": "application/json"}
            
            async with self.session.request(method, url, json=data, headers=headers) as response:
                response_text = await response.text()
                response_time = time.time() - start_time
                response_size = len(response_text)
                
                metric = PerformanceMetrics(
                    endpoint=endpoint,
                    method=method,
                    response_time=response_time,
                    status_code=response.status,
                    success=200 <= response.status < 300,
                    timestamp=timestamp,
                    payload_size=payload_size,
                    response_size=response_size
                )
                
                self.monitor.log_metric(metric)
                return metric
                
        except Exception as e:
            response_time = time.time() - start_time
            metric = PerformanceMetrics(
                endpoint=endpoint,
                method=method,
                response_time=response_time,
                status_code=0,
                success=False,
                timestamp=timestamp,
                payload_size=payload_size,
                response_size=0
            )
            self.monitor.log_metric(metric)
            return metric
    
    async def health_check_load_test(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Load test the health endpoint"""
        print(f"Running health check load test for {duration_seconds} seconds with {self.concurrent_users} concurrent users...")
        
        end_time = time.time() + duration_seconds
        tasks = []
        
        async def health_check_worker():
            while time.time() < end_time:
                await self.make_request("GET", "/api/v1/health")
                await asyncio.sleep(0.1)  # Small delay between requests
        
        # Start concurrent workers
        for _ in range(self.concurrent_users):
            task = asyncio.create_task(health_check_worker())
            tasks.append(task)
        
        # Wait for completion
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return self.monitor.get_summary()
    
    async def hash_lookup_load_test(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Load test hash lookup endpoint"""
        print(f"Running hash lookup load test for {duration_seconds} seconds...")
        
        # Sample hashes for testing
        test_hashes = [
            "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
            "5d41402abc4b2a76b9719d911017c592",
            "a1b2c3d4e5f6",
            "7d865e959b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730"
        ]
        
        end_time = time.time() + duration_seconds
        tasks = []
        
        async def lookup_worker():
            while time.time() < end_time:
                lookup_data = {
                    "hashes": test_hashes[:2],  # Use first 2 hashes
                    "source_system": "grapnel",
                    "include_metadata": False
                }
                await self.make_request("POST", "/api/v1/hashes/lookup", lookup_data)
                await asyncio.sleep(0.2)  # Slightly longer delay for complex operations
        
        # Start concurrent workers
        for _ in range(min(self.concurrent_users, 5)):  # Limit for complex operations
            task = asyncio.create_task(lookup_worker())
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        return self.monitor.get_summary()
    
    async def mixed_workload_test(self, duration_seconds: int = 120) -> Dict[str, Any]:
        """Mixed workload test simulating real usage"""
        print(f"Running mixed workload test for {duration_seconds} seconds...")
        
        end_time = time.time() + duration_seconds
        
        # Different types of workers
        async def health_worker():
            while time.time() < end_time:
                await self.make_request("GET", "/api/v1/health")
                await asyncio.sleep(1)
        
        async def stats_worker():
            while time.time() < end_time:
                await self.make_request("GET", "/api/v1/hashes/stats")
                await asyncio.sleep(5)
        
        async def lookup_worker():
            test_hashes = ["8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"]
            while time.time() < end_time:
                lookup_data = {
                    "hashes": test_hashes,
                    "source_system": "trace",
                    "include_metadata": True
                }
                await self.make_request("POST", "/api/v1/hashes/lookup", lookup_data)
                await asyncio.sleep(2)
        
        async def registration_worker():
            counter = 0
            while time.time() < end_time:
                counter += 1
                hash_value = f"load_test_hash_{counter:06d}_" + "a" * 32
                reg_data = {
                    "hashes": [{
                        "hash_value": hash_value,
                        "hash_type": "SHA256",
                        "source_id": f"load_test_{counter}",
                        "severity": "low",
                        "tags": ["load_test", "automated"]
                    }],
                    "source_system": "takedown"
                }
                await self.make_request("POST", "/api/v1/hashes/register", reg_data)
                await asyncio.sleep(10)  # Less frequent for writes
        
        # Create mixed workload
        tasks = []
        
        # Health checks (frequent)
        for _ in range(2):
            tasks.append(asyncio.create_task(health_worker()))
        
        # Stats checks (less frequent)
        tasks.append(asyncio.create_task(stats_worker()))
        
        # Lookups (moderate frequency)
        for _ in range(3):
            tasks.append(asyncio.create_task(lookup_worker()))
        
        # Registrations (infrequent)
        tasks.append(asyncio.create_task(registration_worker()))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        return self.monitor.get_summary()

class HealthMonitor:
    """Continuous health monitoring"""
    
    def __init__(self, base_url: str, check_interval: int = 30):
        self.base_url = base_url.rstrip('/')
        self.check_interval = check_interval
        self.health_history = []
        self.session = None
    
    async def setup_session(self):
        """Initialize session"""
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def cleanup_session(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> Dict[str, Any]:
        """Single health check"""
        timestamp = datetime.now()
        
        try:
            start_time = time.time()
            async with self.session.get(f"{self.base_url}/api/v1/health") as response:
                response_time = time.time() - start_time
                response_data = await response.json()
                
                health_data = {
                    "timestamp": timestamp.isoformat(),
                    "status": "healthy" if response.status == 200 else "unhealthy",
                    "response_time": response_time,
                    "status_code": response.status,
                    "details": response_data
                }
                
                self.health_history.append(health_data)
                return health_data
                
        except Exception as e:
            health_data = {
                "timestamp": timestamp.isoformat(),
                "status": "error",
                "response_time": None,
                "status_code": 0,
                "error": str(e)
            }
            self.health_history.append(health_data)
            return health_data
    
    async def continuous_monitoring(self, duration_minutes: int = 60):
        """Run continuous health monitoring"""
        print(f"Starting continuous health monitoring for {duration_minutes} minutes...")
        print(f"Checking every {self.check_interval} seconds")
        
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            health_data = await self.check_health()
            
            # Print status
            status_icon = "✅" if health_data["status"] == "healthy" else "❌"
            response_time = health_data.get("response_time", 0)
            print(f"{status_icon} [{datetime.now().strftime('%H:%M:%S')}] "
                  f"Status: {health_data['status']} | "
                  f"Response: {response_time:.3f}s")
            
            # Alert on issues
            if health_data["status"] != "healthy":
                print(f"🚨 ALERT: Health check failed - {health_data.get('error', 'Unknown error')}")
            
            await asyncio.sleep(self.check_interval)
        
        return self.get_health_summary()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health monitoring summary"""
        if not self.health_history:
            return {"error": "No health data collected"}
        
        total_checks = len(self.health_history)
        healthy_checks = sum(1 for h in self.health_history if h["status"] == "healthy")
        
        response_times = [h["response_time"] for h in self.health_history 
                         if h["response_time"] is not None]
        
        return {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "uptime_percentage": (healthy_checks / total_checks) * 100,
            "response_times": {
                "avg": statistics.mean(response_times) if response_times else 0,
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0
            },
            "issues": [h for h in self.health_history if h["status"] != "healthy"]
        }

async def run_performance_benchmark(base_url: str):
    """Run comprehensive performance benchmark"""
    print("🚀 Starting Performance Benchmark")
    print("=" * 50)
    
    load_tester = LoadTester(base_url, concurrent_users=5)
    
    try:
        await load_tester.setup_session()
        
        # Test 1: Health endpoint load test
        print("\n📊 Test 1: Health Endpoint Load Test")
        health_results = await load_tester.health_check_load_test(30)
        print(f"Requests: {health_results['total_requests']}")
        print(f"Success Rate: {health_results['success_rate']:.1f}%")
        print(f"Avg Response Time: {health_results['response_times']['avg']:.3f}s")
        print(f"P95 Response Time: {health_results['response_times']['p95']:.3f}s")
        
        # Reset metrics for next test
        load_tester.monitor = SystemMonitor()
        
        # Test 2: Hash lookup load test
        print("\n🔍 Test 2: Hash Lookup Load Test")
        lookup_results = await load_tester.hash_lookup_load_test(30)
        print(f"Requests: {lookup_results['total_requests']}")
        print(f"Success Rate: {lookup_results['success_rate']:.1f}%")
        print(f"Avg Response Time: {lookup_results['response_times']['avg']:.3f}s")
        print(f"P99 Response Time: {lookup_results['response_times']['p99']:.3f}s")
        
        # Reset metrics for final test
        load_tester.monitor = SystemMonitor()
        
        # Test 3: Mixed workload
        print("\n🔄 Test 3: Mixed Workload Test")
        mixed_results = await load_tester.mixed_workload_test(60)
        print(f"Total Requests: {mixed_results['total_requests']}")
        print(f"Success Rate: {mixed_results['success_rate']:.1f}%")
        print(f"Avg Response Time: {mixed_results['response_times']['avg']:.3f}s")
        
        # Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_results_{timestamp}.csv"
        load_tester.monitor.export_to_csv(filename)
        print(f"\n📁 Results exported to: {filename}")
        
        return mixed_results
        
    finally:
        await load_tester.cleanup_session()

async def run_health_monitoring(base_url: str, duration_minutes: int):
    """Run continuous health monitoring"""
    health_monitor = HealthMonitor(base_url, check_interval=30)
    
    try:
        await health_monitor.setup_session()
        summary = await health_monitor.continuous_monitoring(duration_minutes)
        
        print("\n📋 Health Monitoring Summary")
        print("=" * 30)
        print(f"Total Checks: {summary['total_checks']}")
        print(f"Uptime: {summary['uptime_percentage']:.2f}%")
        print(f"Avg Response Time: {summary['response_times']['avg']:.3f}s")
        
        if summary['issues']:
            print(f"\n⚠️ Issues Found: {len(summary['issues'])}")
            for issue in summary['issues'][:5]:  # Show first 5 issues
                print(f"  - {issue['timestamp']}: {issue.get('error', 'Unknown')}")
        
        return summary
        
    finally:
        await health_monitor.cleanup_session()

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Grapnel API Monitoring & Load Testing")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--mode", choices=["test", "benchmark", "monitor"], 
                       default="test", help="Operation mode")
    parser.add_argument("--duration", type=int, default=60, 
                       help="Duration in minutes for monitoring mode")
    parser.add_argument("--users", type=int, default=10,
                       help="Concurrent users for load testing")
    
    args = parser.parse_args()
    
    print(f"🎯 Target URL: {args.url}")
    print(f"📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        if args.mode == "benchmark":
            await run_performance_benchmark(args.url)
        elif args.mode == "monitor":
            await run_health_monitoring(args.url, args.duration)
        else:
            # Run the comprehensive test suite (from previous script)
            from test_api import GrapnelAPITester
            tester = GrapnelAPITester(args.url)
            await tester.run_all_tests()
            
    except KeyboardInterrupt:
        print("\n⏹️ Operation interrupted by user")
    except Exception as e:
        print(f"\n❌ Operation failed: {e}")

if __name__ == "__main__":
    # Install required packages if not present
    try:
        import psutil
    except ImportError:
        print("Installing required package: psutil")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
    
    asyncio.run(main())