#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import glob
import os

def parse_junit_results():
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'errors': 0,
        'skipped': 0,
        'suites': []
    }
    
    junit_files = glob.glob('test-reports/*-junit.xml')
    print(f"Found {len(junit_files)} JUnit files:")
    
    for junit_file in junit_files:
        print(f"  Processing: {junit_file}")
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            # Handle testsuites root element or direct testsuite element
            if root.tag == 'testsuites':
                testsuites = root.findall('testsuite')
            else:
                testsuites = [root]
            
            suite_tests = 0
            suite_failures = 0
            suite_errors = 0
            suite_skipped = 0
            
            for testsuite in testsuites:
                tests = int(testsuite.get('tests', 0))
                failures = int(testsuite.get('failures', 0))
                errors = int(testsuite.get('errors', 0))
                skipped = int(testsuite.get('skipped', 0))
                
                suite_tests += tests
                suite_failures += failures
                suite_errors += errors
                suite_skipped += skipped
            
            passed = suite_tests - suite_failures - suite_errors - suite_skipped
            suite_name = os.path.basename(junit_file).replace('-junit.xml', '')
            
            results['total'] += suite_tests
            results['passed'] += passed
            results['failed'] += suite_failures
            results['errors'] += suite_errors
            results['skipped'] += suite_skipped
            
            results['suites'].append({
                'name': suite_name,
                'tests': suite_tests,
                'passed': passed,
                'failed': suite_failures,
                'errors': suite_errors,
                'skipped': suite_skipped
            })
            
            print(f"    Tests: {suite_tests}, Passed: {passed}, Failed: {suite_failures}, Errors: {suite_errors}")
            
        except Exception as e:
            print(f"Error parsing {junit_file}: {e}")
    
    return results

def generate_summary(results):
    print("\n" + "="*60)
    print("CI Test Results Summary")
    print("="*60)
    print(f"Total tests: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Errors: {results['errors']}")
    print(f"Skipped: {results['skipped']}")
    
    if results['total'] > 0:
        pass_rate = (results['passed'] / results['total']) * 100
        print(f"Pass rate: {pass_rate:.1f}%")
    
    print("\nTest suite details:")
    for suite in results['suites']:
        status = "PASS" if suite['failed'] == 0 and suite['errors'] == 0 else "FAIL"
        print(f"  {status} {suite['name']}: {suite['tests']} tests")
    
    # Determine overall result
    all_passed = results['failed'] == 0 and results['errors'] == 0
    overall_status = "PASS" if all_passed else "FAIL"
    
    print(f"\nOverall result: {overall_status}")
    
    # Set GitHub Actions output
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"tests_passed={str(all_passed).lower()}\n")
            f.write(f"total_tests={results['total']}\n")
            f.write(f"failed_tests={results['failed']}\n")
            f.write(f"error_tests={results['errors']}\n")
    
    return all_passed

def main():
    results = parse_junit_results()
    success = generate_summary(results)
    
    if not success:
        print("\nTests failed, CI will exit with error code")
        exit(1)
    else:
        print("\nAll tests passed, CI completed successfully")

if __name__ == '__main__':
    main() 