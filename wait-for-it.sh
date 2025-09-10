#!/bin/bash

# wait-for-it.sh - Wait for services to be ready
# Usage: ./wait-for-it.sh [options]
# Options:
#   -h, --help     Show this help message
#   -t, --timeout  Timeout in seconds (default: 30)
#   -v, --verbose  Verbose output

set -e

# Default values
TIMEOUT=30
VERBOSE=false
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
REDIS_HOST="localhost"
REDIS_PORT="6379"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to show help
show_help() {
    cat << EOF
wait-for-it.sh - Wait for PostgreSQL and Redis to be ready

USAGE:
    ./wait-for-it.sh [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    -t, --timeout SEC   Timeout in seconds (default: 30)
    -v, --verbose       Enable verbose output
    --postgres-host HOST PostgreSQL host (default: localhost)
    --postgres-port PORT PostgreSQL port (default: 5432)
    --redis-host HOST   Redis host (default: localhost)
    --redis-port PORT   Redis port (default: 6379)

EXAMPLES:
    ./wait-for-it.sh
    ./wait-for-it.sh --timeout 60 --verbose
    ./wait-for-it.sh --postgres-host db.example.com --postgres-port 5433

EXIT CODES:
    0 - All services are ready
    1 - Timeout waiting for services
    2 - Invalid arguments
    3 - PostgreSQL not ready
    4 - Redis not ready
EOF
}

# Function to check if a service is ready
check_service() {
    local host=$1
    local port=$2
    local service_name=$3
    
    if command -v nc >/dev/null 2>&1; then
        # Use netcat if available
        nc -z "$host" "$port" 2>/dev/null
    elif command -v telnet >/dev/null 2>&1; then
        # Fallback to telnet
        timeout 1 telnet "$host" "$port" >/dev/null 2>&1
    else
        # Fallback to bash built-in
        timeout 1 bash -c "exec 3<>/dev/tcp/$host/$port" 2>/dev/null
    fi
}

# Function to wait for a service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=$4
    local verbose=$5
    
    local start_time=$(date +%s)
    local end_time=$((start_time + timeout))
    
    if [ "$verbose" = true ]; then
        print_status $YELLOW "Waiting for $service_name on $host:$port (timeout: ${timeout}s)..."
    fi
    
    while [ $(date +%s) -lt $end_time ]; do
        if check_service "$host" "$port" "$service_name"; then
            if [ "$verbose" = true ]; then
                print_status $GREEN "✓ $service_name is ready on $host:$port"
            fi
            return 0
        fi
        
        if [ "$verbose" = true ]; then
            echo -n "."
        fi
        
        sleep 1
    done
    
    if [ "$verbose" = true ]; then
        echo ""
        print_status $RED "✗ Timeout waiting for $service_name on $host:$port"
    fi
    
    return 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --postgres-host)
            POSTGRES_HOST="$2"
            shift 2
            ;;
        --postgres-port)
            POSTGRES_PORT="$2"
            shift 2
            ;;
        --redis-host)
            REDIS_HOST="$2"
            shift 2
            ;;
        --redis-port)
            REDIS_PORT="$2"
            shift 2
            ;;
        *)
            print_status $RED "Unknown option: $1"
            show_help
            exit 2
            ;;
    esac
done

# Validate timeout is a number
if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
    print_status $RED "Error: Timeout must be a positive integer"
    exit 2
fi

# Main execution
print_status $YELLOW "Starting service readiness check..."

# Wait for PostgreSQL
if ! wait_for_service "$POSTGRES_HOST" "$POSTGRES_PORT" "PostgreSQL" "$TIMEOUT" "$VERBOSE"; then
    print_status $RED "Error: PostgreSQL is not ready on $POSTGRES_HOST:$POSTGRES_PORT"
    exit 3
fi

# Wait for Redis
if ! wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" "$TIMEOUT" "$VERBOSE"; then
    print_status $RED "Error: Redis is not ready on $REDIS_HOST:$REDIS_PORT"
    exit 4
fi

print_status $GREEN "✓ All services are ready!"
exit 0
