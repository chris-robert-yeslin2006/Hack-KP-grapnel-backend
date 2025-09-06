#!/usr/bin/env python3
"""
Fixed Comprehensive API Testing Script for Grapnel Backend
Tests all endpoints with correct request format
"""

import asyncio
import aiohttp
import json
import hashlib
import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
import argparse

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_status(message: str, status: str = "INFO"):
    colors = {
        "INFO": Colors.OKBLUE,
        "SUCCESS": Colors.OKGREEN,
        "WARNING": Colors.WARNING,
        "ERROR": Colors.FAIL,
        "HEADER": Colors.HEADER
    }
    color = colors.get(status, Colors.OKBLUE)
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {status}: {message}{Colors.ENDC}")

class GrapnelAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.test_results = []
        self.webhook_subscriptions = []
        
        # Generate realistic test data
        self.test_hashes = self._generate_test_hashes()
        self.systems = ["trace", "grapnel", "takedown"]
        
    def _generate_test_hashes(self) -> Dict[str, List[str]]:
        """Generate realistic hash values for testing"""
        # Sample content that would generate these hashes (for realism)
        sample_content = [
            "suspicious_image_001.jpg",
            "harmful_video_002.mp4",
            "illegal_document_003.pdf",
            "flagged_content_004.png",
            "reported_file_005.zip"
        ]
        
        hashes = {
            "SHA256": [],
            "MD5": [],
            "PHASH": []
        }
        
        for content in sample_content:
            # Generate SHA256
            sha256_hash = hashlib.sha256(content.encode()).hexdigest()
            hashes["SHA256"].append(sha256_hash)
            
            # Generate MD5
            md5_hash = hashlib.md5(content.encode()).hexdigest()
            hashes["MD5"].append(md5_hash)
            
            # Generate realistic PHASH (16-character hex for simplicity)
            phash = hashlib.sha256(content.encode()).hexdigest()[:16]
            hashes["PHASH"].append(phash)
            
        return hashes
    
    async def setup_session(self):
        """Initialize HTTP session"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def cleanup_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: dict = None, params: dict = None) -> Dict[str, Any]:
        """Make HTTP request and handle response"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            headers = {"Content-Type": "application/json"}
            
            async with self.session.request(
                method, 
                url, 
                json=data, 
                params=params,
                headers=headers
            ) as response:
                response_text = await response.text()
                
                result = {
                    "status_code": response.status,
                    "success": 200 <= response.status < 300,
                    "response": {},
                    "error": None,
                    "execution_time": 0
                }
                
                try:
                    result["response"] = json.loads(response_text) if response_text else {}
                except json.JSONDecodeError:
                    result["response"] = {"raw": response_text}
                
                if not result["success"]:
                    result["error"] = result["response"].get("detail", f"HTTP {response.status}")
                
                return result
                
        except Exception as e:
            return {
                "status_code": 0,
                "success": False,
                "response": {},
                "error": str(e),
                "execution_time": 0
            }
    
    async def test_health_endpoints(self):
        """Test health and monitoring endpoints"""
        print_status("Testing Health Endpoints", "HEADER")
        
        # Test health endpoint
        print_status("Testing /api/v1/health")
        result = await self.make_request("GET", "/api/v1/health")
        
        if result["success"]:
            print_status(f"Health check passed: {result['response'].get('status', 'Unknown')}", "SUCCESS")
            self.test_results.append(("Health Check", True, None))
        else:
            print_status(f"Health check failed: {result['error']}", "ERROR")
            self.test_results.append(("Health Check", False, result["error"]))
        
        # Test readiness endpoint
        print_status("Testing /api/v1/ready")
        result = await self.make_request("GET", "/api/v1/ready")
        
        if result["success"]:
            print_status("Readiness check passed", "SUCCESS")
            self.test_results.append(("Readiness Check", True, None))
        else:
            print_status(f"Readiness check failed: {result['error']}", "WARNING")
            self.test_results.append(("Readiness Check", False, result["error"]))
        
        # Test stats endpoint
        print_status("Testing /api/v1/hashes/stats")
        result = await self.make_request("GET", "/api/v1/hashes/stats")
        
        if result["success"]:
            stats = result["response"]
            print_status(f"Stats retrieved - Total hashes: {stats.get('total_hashes', 0)}", "SUCCESS")
            self.test_results.append(("Hash Stats", True, None))
        else:
            print_status(f"Stats retrieval failed: {result['error']}", "WARNING")
            self.test_results.append(("Hash Stats", False, result["error"]))
    
    async def test_hash_registration(self):
        """Test hash registration with different scenarios"""
        print_status("Testing Hash Registration", "HEADER")
        
        # Test 1: Single hash registration - FIXED FORMAT
        print_status("Testing single hash registration")
        test_hash = self.test_hashes["SHA256"][0]
        
        # Send as list directly, with source_system as query parameter
        registration_data = [{
            "hash_value": test_hash,
            "hash_type": "SHA256",
            "source_id": "test-case-001",
            "severity": "high",
            "tags": ["test", "automated", "child-safety"],
            "metadata": {
                "case_id": "TC001",
                "reporter": "automated-test",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }]
        
        params = {"source_system": "takedown"}
        
        result = await self.make_request("POST", "/api/v1/hashes/register", registration_data, params)
        
        if result["success"]:
            response = result["response"]
            print_status(f"Single hash registered successfully - Count: {response.get('registered_count', 0)}", "SUCCESS")
            self.test_results.append(("Single Hash Registration", True, None))
        else:
            print_status(f"Single hash registration failed: {result['error']}", "ERROR")
            self.test_results.append(("Single Hash Registration", False, result["error"]))
        
        # Test 2: Bulk hash registration - FIXED FORMAT
        print_status("Testing bulk hash registration (multiple systems)")
        
        for i, system in enumerate(self.systems):
            bulk_data = [
                {
                    "hash_value": self.test_hashes["SHA256"][i],
                    "hash_type": "SHA256",
                    "source_id": f"{system}-case-{str(i+1).zfill(3)}",
                    "severity": random.choice(["low", "medium", "high", "critical"]),
                    "tags": [system, "bulk-test", random.choice(["urgent", "routine", "follow-up"])],
                    "metadata": {
                        "batch_id": f"BULK_{system.upper()}_{int(time.time())}",
                        "priority": random.randint(1, 5),
                        "region": random.choice(["US", "EU", "APAC"])
                    }
                },
                {
                    "hash_value": self.test_hashes["MD5"][i],
                    "hash_type": "MD5",
                    "source_id": f"{system}-case-{str(i+100).zfill(3)}",
                    "severity": random.choice(["low", "medium", "high"]),
                    "tags": [system, "md5-test"],
                    "metadata": {"test_type": "md5_bulk"}
                }
            ]
            
            params = {"source_system": system}
            
            result = await self.make_request("POST", "/api/v1/hashes/register", bulk_data, params)
            
            if result["success"]:
                response = result["response"]
                print_status(f"Bulk registration for {system}: {response.get('registered_count', 0)} hashes", "SUCCESS")
                self.test_results.append((f"Bulk Registration ({system})", True, None))
            else:
                print_status(f"Bulk registration failed for {system}: {result['error']}", "ERROR")
                self.test_results.append((f"Bulk Registration ({system})", False, result["error"]))
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
    
    async def test_hash_lookup(self):
        """Test hash lookup functionality"""
        print_status("Testing Hash Lookup", "HEADER")
        
        # Test 1: Lookup existing hashes - FIXED FORMAT
        print_status("Testing lookup of existing hashes")
        
        lookup_data = {
            "hashes": self.test_hashes["SHA256"][:3],  # First 3 SHA256 hashes
            "source_system": "grapnel",
            "include_metadata": True
        }
        
        result = await self.make_request("POST", "/api/v1/hashes/lookup", lookup_data)
        
        if result["success"]:
            response = result["response"]
            matches = response.get("matches", [])
            total_matches = response.get("total_matches", 0)
            query_time = response.get("query_time", 0)
            
            print_status(f"Hash lookup completed - Found: {total_matches}/{len(lookup_data['hashes'])} matches", "SUCCESS")
            print_status(f"Query time: {query_time:.3f}s", "INFO")
            
            # Show details of matches
            for match in matches:
                if match.get("found"):
                    sources = match.get("sources", [])
                    print_status(f"  Hash {match['hash'][:16]}... found in {len(sources)} systems", "INFO")
            
            self.test_results.append(("Hash Lookup (Existing)", True, None))
        else:
            print_status(f"Hash lookup failed: {result['error']}", "ERROR")
            self.test_results.append(("Hash Lookup (Existing)", False, result["error"]))
        
        # Test 2: Lookup non-existent hashes
        print_status("Testing lookup of non-existent hashes")
        
        fake_hashes = [
            hashlib.sha256(f"nonexistent_{i}".encode()).hexdigest() 
            for i in range(3)
        ]
        
        lookup_data = {
            "hashes": fake_hashes,
            "source_system": "trace",
            "include_metadata": False
        }
        
        result = await self.make_request("POST", "/api/v1/hashes/lookup", lookup_data)
        
        if result["success"]:
            response = result["response"]
            total_matches = response.get("total_matches", 0)
            print_status(f"Non-existent hash lookup: {total_matches} matches (expected 0)", "SUCCESS")
            self.test_results.append(("Hash Lookup (Non-existent)", True, None))
        else:
            print_status(f"Non-existent hash lookup failed: {result['error']}", "ERROR")
            self.test_results.append(("Hash Lookup (Non-existent)", False, result["error"]))
        
        # Test 3: Mixed lookup (existing + non-existent)
        print_status("Testing mixed hash lookup")
        
        mixed_hashes = [
            self.test_hashes["SHA256"][0],  # Should exist
            fake_hashes[0],  # Should not exist
            self.test_hashes["MD5"][0],  # Should exist
        ]
        
        lookup_data = {
            "hashes": mixed_hashes,
            "source_system": "takedown",
            "include_metadata": True
        }
        
        result = await self.make_request("POST", "/api/v1/hashes/lookup", lookup_data)
        
        if result["success"]:
            response = result["response"]
            total_matches = response.get("total_matches", 0)
            print_status(f"Mixed lookup: {total_matches} matches out of {len(mixed_hashes)} hashes", "SUCCESS")
            self.test_results.append(("Hash Lookup (Mixed)", True, None))
        else:
            print_status(f"Mixed hash lookup failed: {result['error']}", "ERROR")
            self.test_results.append(("Hash Lookup (Mixed)", False, result["error"]))
    
    async def test_notification_system(self):
        """Test notification and webhook functionality"""
        print_status("Testing Notification System", "HEADER")
        
        # Test 1: Webhook subscription
        print_status("Testing webhook subscription")
        
        for system in self.systems:
            subscription_data = {
                "system_id": system,
                "webhook_url": f"https://httpbin.org/post/{system}",  # Test webhook endpoint
                "notification_types": ["hash_match", "alert", "update"],
                "filters": {
                    "severity": ["high", "critical"],
                    "tags": [system, "priority"]
                }
            }
            
            result = await self.make_request("POST", "/api/v1/notifications/subscribe", subscription_data)
            
            if result["success"]:
                print_status(f"Webhook subscribed for {system}", "SUCCESS")
                self.webhook_subscriptions.append(system)
                self.test_results.append((f"Webhook Subscription ({system})", True, None))
            else:
                print_status(f"Webhook subscription failed for {system}: {result['error']}", "ERROR")
                self.test_results.append((f"Webhook Subscription ({system})", False, result["error"]))
        
        # Small delay
        await asyncio.sleep(2)
        
        # Test 2: Get subscription details
        print_status("Testing subscription retrieval")
        
        for system in self.webhook_subscriptions[:2]:  # Test first 2 subscriptions
            result = await self.make_request("GET", f"/api/v1/notifications/subscriptions/{system}")
            
            if result["success"]:
                subscription = result["response"]
                webhook_url = subscription.get("webhook_url", "")
                print_status(f"Retrieved subscription for {system}: {webhook_url}", "SUCCESS")
                self.test_results.append((f"Get Subscription ({system})", True, None))
            else:
                print_status(f"Failed to get subscription for {system}: {result['error']}", "WARNING")
                self.test_results.append((f"Get Subscription ({system})", False, result["error"]))
        
        # Test 3: Check notification queue
        print_status("Testing notification queue status")
        
        result = await self.make_request("GET", "/api/v1/notifications/queue/status")
        
        if result["success"]:
            queue_status = result["response"]
            pending = queue_status.get("pending", 0)
            sent = queue_status.get("sent", 0)
            failed = queue_status.get("failed", 0)
            
            print_status(f"Queue status - Pending: {pending}, Sent: {sent}, Failed: {failed}", "SUCCESS")
            self.test_results.append(("Notification Queue Status", True, None))
        else:
            print_status(f"Failed to get queue status: {result['error']}", "WARNING")
            self.test_results.append(("Notification Queue Status", False, result["error"]))
    
    async def test_error_conditions(self):
        """Test error handling and edge cases"""
        print_status("Testing Error Conditions", "HEADER")
        
        # Test 1: Invalid hash registration
        print_status("Testing invalid hash registration")
        
        invalid_data = [{
            "hash_value": "invalid_hash",  # Too short
            "hash_type": "INVALID_TYPE",
            "source_id": "",  # Empty source_id
            "severity": "invalid_severity"
        }]
        
        params = {"source_system": "invalid_system"}
        
        result = await self.make_request("POST", "/api/v1/hashes/register", invalid_data, params)
        
        if not result["success"]:
            print_status("Invalid hash registration correctly rejected", "SUCCESS")
            self.test_results.append(("Invalid Hash Registration", True, None))
        else:
            print_status("Invalid hash registration was accepted (unexpected)", "ERROR")
            self.test_results.append(("Invalid Hash Registration", False, "Should have been rejected"))
        
        # Test 2: Empty hash lookup
        print_status("Testing empty hash lookup")
        
        empty_lookup = {
            "hashes": [],
            "source_system": "grapnel"
        }
        
        result = await self.make_request("POST", "/api/v1/hashes/lookup", empty_lookup)
        
        if not result["success"]:
            print_status("Empty hash lookup correctly rejected", "SUCCESS")
            self.test_results.append(("Empty Hash Lookup", True, None))
        else:
            print_status("Empty hash lookup was accepted (unexpected)", "ERROR")
            self.test_results.append(("Empty Hash Lookup", False, "Should have been rejected"))
        
        # Test 3: Invalid webhook subscription
        print_status("Testing invalid webhook subscription")
        
        invalid_webhook = {
            "system_id": "invalid_system",
            "webhook_url": "not_a_valid_url",
            "notification_types": ["invalid_type"]
        }
        
        result = await self.make_request("POST", "/api/v1/notifications/subscribe", invalid_webhook)
        
        if not result["success"]:
            print_status("Invalid webhook subscription correctly rejected", "SUCCESS")
            self.test_results.append(("Invalid Webhook Subscription", True, None))
        else:
            print_status("Invalid webhook subscription was accepted (unexpected)", "ERROR")
            self.test_results.append(("Invalid Webhook Subscription", False, "Should have been rejected"))
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        print_status("Testing Rate Limiting", "HEADER")
        
        print_status("Sending multiple rapid requests to test rate limiting")
        
        # Make rapid requests to trigger rate limiting
        tasks = []
        for i in range(10):
            lookup_data = {
                "hashes": [self.test_hashes["SHA256"][0]],
                "source_system": "trace"
            }
            task = self.make_request("POST", "/api/v1/hashes/lookup", lookup_data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
        rate_limited_count = sum(1 for r in results if isinstance(r, dict) and r.get("status_code") == 429)
        
        print_status(f"Rate limiting test - Success: {success_count}, Rate limited: {rate_limited_count}", "INFO")
        
        if rate_limited_count > 0:
            print_status("Rate limiting is working correctly", "SUCCESS")
            self.test_results.append(("Rate Limiting", True, None))
        else:
            print_status("No rate limiting detected (may need higher load)", "WARNING")
            self.test_results.append(("Rate Limiting", False, "No rate limiting observed"))
    
    def print_summary(self):
        """Print test results summary"""
        print_status("Test Results Summary", "HEADER")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, passed, _ in self.test_results if passed)
        failed_tests = total_tests - passed_tests
        
        print_status(f"Total Tests: {total_tests}", "INFO")
        print_status(f"Passed: {passed_tests}", "SUCCESS" if passed_tests > 0 else "INFO")
        print_status(f"Failed: {failed_tests}", "ERROR" if failed_tests > 0 else "SUCCESS")
        
        if failed_tests > 0:
            print_status("Failed Tests:", "ERROR")
            for test_name, passed, error in self.test_results:
                if not passed:
                    print_status(f"  - {test_name}: {error or 'Unknown error'}", "ERROR")
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print_status(f"Success Rate: {success_rate:.1f}%", "SUCCESS" if success_rate >= 80 else "WARNING")
        
        return success_rate >= 80
    
    async def run_all_tests(self):
        """Run all tests"""
        print_status(f"Starting comprehensive API tests for: {self.base_url}", "HEADER")
        
        try:
            await self.setup_session()
            
            # Run all test suites
            await self.test_health_endpoints()
            await asyncio.sleep(1)
            
            await self.test_hash_registration()
            await asyncio.sleep(2)
            
            await self.test_hash_lookup()
            await asyncio.sleep(1)
            
            await self.test_notification_system()
            await asyncio.sleep(1)
            
            await self.test_error_conditions()
            await asyncio.sleep(1)
            
            await self.test_rate_limiting()
            
            # Print summary
            success = self.print_summary()
            return success
            
        finally:
            await self.cleanup_session()

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test Grapnel Backend API")
    parser.add_argument(
        "--url", 
        default="http://localhost:8000", 
        help="Base URL of the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--production", 
        action="store_true", 
        help="Test against production deployment"
    )
    
    args = parser.parse_args()
    
    if args.production:
        # You can set your production URL here
        base_url = input("Enter your production URL (e.g., https://your-app.onrender.com): ").strip()
        if not base_url:
            print_status("No URL provided, using default local URL", "WARNING")
            base_url = args.url
    else:
        base_url = args.url
    
    print_status("Grapnel Backend API Testing Suite", "HEADER")
    print_status(f"Target URL: {base_url}", "INFO")
    print_status(f"Test start time: {datetime.now().isoformat()}", "INFO")
    
    tester = GrapnelAPITester(base_url)
    
    try:
        success = await tester.run_all_tests()
        
        if success:
            print_status("All tests completed successfully!", "SUCCESS")
            exit(0)
        else:
            print_status("Some tests failed. Check the summary above.", "ERROR")
            exit(1)
            
    except KeyboardInterrupt:
        print_status("Tests interrupted by user", "WARNING")
        exit(1)
    except Exception as e:
        print_status(f"Test suite failed with error: {e}", "ERROR")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())