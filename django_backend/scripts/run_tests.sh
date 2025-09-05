#!/bin/bash

# Test runner script for Task Management System
# This script provides convenient ways to run different test suites

echo "🧪 Task Management System - Test Runner"
echo "======================================="

cd "$(dirname "$0")/.."

export DJANGO_SETTINGS_MODULE=config.test_settings

run_tests() {
    local test_path=$1
    local description=$2
    
    echo ""
    echo "🔍 Running $description..."
    echo "Command: python manage.py test $test_path --verbosity=2"
    echo "----------------------------------------"
    python manage.py test $test_path --verbosity=2
    
    if [ $? -eq 0 ]; then
        echo "✅ $description - PASSED"
    else
        echo "❌ $description - FAILED"
        return 1
    fi
}

case "${1:-all}" in
    "models")
        echo "Running only model tests..."
        run_tests "apps.tasks.tests.test_models apps.users.tests.test_models" "Model Tests"
        ;;
    "api")
        echo "Running only API tests..."
        run_tests "apps.tasks.tests.test_api apps.users.tests.test_api" "API Tests"
        ;;
    "tasks")
        echo "Running only Tasks app tests..."
        run_tests "apps.tasks" "Tasks App Tests"
        ;;
    "users")
        echo "Running only Users app tests..."
        run_tests "apps.users" "Users App Tests"
        ;;
    "common")
        echo "Running only Common app tests..."
        run_tests "apps.common" "Common App Tests (JWT, RSA, Auth)"
        ;;
    "jwt"|"rsa")
        echo "Running only RSA JWT tests..."
        run_tests "apps.common.tests.test_rsa_jwt" "RSA JWT Tests"
        ;;
    "coverage")
        echo "Running tests with coverage report..."
        echo "Installing coverage if not present..."
        pip install coverage
        echo "Running tests with coverage..."
        coverage run --source='.' manage.py test --verbosity=2
        echo "Generating coverage report..."
        coverage report
        coverage html
        echo "📊 Coverage report generated in htmlcov/"
        ;;
    "all"|*)
        echo "Running all tests..."
        
        # Run each test suite separately for better reporting
        run_tests "apps.tasks.tests.test_models" "Tasks Model Tests"
        run_tests "apps.tasks.tests.test_api" "Tasks API Tests"
        run_tests "apps.users.tests.test_models" "Users Model Tests"
        run_tests "apps.users.tests.test_api" "Users API Tests"
        run_tests "apps.common.tests.test_rsa_jwt" "RSA JWT Tests"
        
        echo ""
        echo "🎉 All test suites completed!"
        echo "Summary:"
        echo "- Tasks Model Tests"
        echo "- Tasks API Tests" 
        echo "- Users Model Tests"
        echo "- Users API Tests"
        echo "- RSA JWT Tests"
        ;;
esac

echo ""
echo "📝 Usage examples:"
echo "  scripts/run_tests.sh all      # Run all tests"
echo "  scripts/run_tests.sh models   # Run only model tests"
echo "  scripts/run_tests.sh api      # Run only API tests"
echo "  scripts/run_tests.sh tasks    # Run only tasks app tests"
echo "  scripts/run_tests.sh users    # Run only users app tests"
echo "  scripts/run_tests.sh common   # Run only common app tests"
echo "  scripts/run_tests.sh jwt      # Run only RSA JWT tests"
echo "  scripts/run_tests.sh rsa      # Run only RSA JWT tests (alias)"
echo "  scripts/run_tests.sh coverage # Run with coverage report"

