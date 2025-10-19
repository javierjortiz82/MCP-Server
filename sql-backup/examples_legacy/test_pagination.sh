#!/bin/bash
# ============================================================================
# Pagination Persistence - Quick Testing Script
# ============================================================================
# This script provides quick commands to test the pagination persistence
# functionality from the command line.
#
# Usage:
#   chmod +x test_pagination.sh
#   ./test_pagination.sh [command]
#
# Commands:
#   view-all      - View all pagination contexts
#   view-recent   - View 10 most recent contexts
#   insert-test   - Insert test data
#   cleanup       - Run cleanup function
#   stats         - Show statistics
# ============================================================================

DB_HOST="localhost"
DB_PORT="5434"
DB_NAME="mcpdb"
DB_USER="mcp_user"
DB_PASSWORD="mcp_password"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# PostgreSQL connection string
PSQL_CMD="PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"

# ============================================================================
# Function: View All Contexts
# ============================================================================
view_all() {
    echo -e "${BLUE}📊 All Pagination Contexts${NC}"
    $PSQL_CMD -c "
        SELECT
            id,
            LEFT(session_id::text, 8) as session,
            category,
            tool_name,
            current_page,
            page_size,
            total_items,
            jsonb_array_length(products) as products_count,
            created_at,
            CASE
                WHEN expires_at IS NULL THEN 'Never'
                WHEN expires_at > CURRENT_TIMESTAMP THEN 'Active'
                ELSE 'Expired'
            END as status
        FROM test.pagination_contexts
        ORDER BY created_at DESC;
    "
}

# ============================================================================
# Function: View Recent Contexts
# ============================================================================
view_recent() {
    echo -e "${BLUE}🕒 10 Most Recent Contexts${NC}"
    $PSQL_CMD -c "
        SELECT
            LEFT(session_id::text, 8) as session,
            category,
            current_page || '/' || CEIL(total_items::float / page_size) as page,
            total_items,
            created_at,
            updated_at
        FROM test.pagination_contexts
        ORDER BY created_at DESC
        LIMIT 10;
    "
}

# ============================================================================
# Function: Insert Test Data
# ============================================================================
insert_test() {
    echo -e "${YELLOW}➕ Inserting Test Pagination Context${NC}"

    TEST_SESSION_ID=$(uuidgen 2>/dev/null || echo "12345678-1234-5678-1234-567812345678")
    echo -e "${GREEN}Session ID: $TEST_SESSION_ID${NC}"

    $PSQL_CMD -c "
        INSERT INTO test.pagination_contexts (
            session_id,
            category,
            tool_name,
            query,
            current_page,
            page_size,
            total_items,
            products,
            expires_at
        ) VALUES (
            '$TEST_SESSION_ID',
            'laptops gaming baratos estudiantes',
            'search_products',
            'laptops gaming baratos para estudiantes',
            0,
            4,
            12,
            '[
                {\"id\": \"LAPTOP001\", \"name\": \"Laptop Gaming Acer Nitro 5\", \"price\": 899.99},
                {\"id\": \"LAPTOP002\", \"name\": \"Laptop Gaming ASUS TUF\", \"price\": 799.99},
                {\"id\": \"LAPTOP003\", \"name\": \"Laptop Gaming HP Pavilion\", \"price\": 749.99},
                {\"id\": \"LAPTOP004\", \"name\": \"Laptop Gaming Lenovo Legion\", \"price\": 999.99},
                {\"id\": \"LAPTOP005\", \"name\": \"Laptop Gaming MSI GF63\", \"price\": 699.99},
                {\"id\": \"LAPTOP006\", \"name\": \"Laptop Gaming Dell G15\", \"price\": 849.99},
                {\"id\": \"LAPTOP007\", \"name\": \"Laptop Gaming Acer Predator\", \"price\": 1299.99},
                {\"id\": \"LAPTOP008\", \"name\": \"Laptop Gaming ASUS ROG\", \"price\": 1499.99},
                {\"id\": \"LAPTOP009\", \"name\": \"Laptop Gaming HP OMEN\", \"price\": 1199.99},
                {\"id\": \"LAPTOP010\", \"name\": \"Laptop Gaming Lenovo IdeaPad\", \"price\": 649.99},
                {\"id\": \"LAPTOP011\", \"name\": \"Laptop Gaming MSI Katana\", \"price\": 899.99},
                {\"id\": \"LAPTOP012\", \"name\": \"Laptop Gaming Dell Alienware\", \"price\": 1799.99}
            ]'::jsonb,
            CURRENT_TIMESTAMP + INTERVAL '24 hours'
        )
        ON CONFLICT (session_id, category)
        DO UPDATE SET
            current_page = EXCLUDED.current_page,
            updated_at = CURRENT_TIMESTAMP;
    "

    echo -e "${GREEN}✅ Test data inserted${NC}"

    # Show inserted data
    $PSQL_CMD -c "
        SELECT
            category,
            current_page,
            page_size,
            total_items,
            jsonb_array_length(products) as products_count,
            created_at
        FROM test.pagination_contexts
        WHERE session_id = '$TEST_SESSION_ID';
    "
}

# ============================================================================
# Function: Run Cleanup
# ============================================================================
cleanup() {
    echo -e "${YELLOW}🧹 Running Cleanup Function${NC}"
    $PSQL_CMD -c "SELECT test.cleanup_expired_pagination_contexts() as deleted_count;"
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# ============================================================================
# Function: Show Statistics
# ============================================================================
stats() {
    echo -e "${BLUE}📈 Pagination Persistence Statistics${NC}"

    echo -e "\n${YELLOW}Total Contexts:${NC}"
    $PSQL_CMD -c "SELECT COUNT(*) as total_contexts FROM test.pagination_contexts;"

    echo -e "\n${YELLOW}Contexts by Status:${NC}"
    $PSQL_CMD -c "
        SELECT
            CASE
                WHEN expires_at IS NULL THEN 'Never Expires'
                WHEN expires_at > CURRENT_TIMESTAMP THEN 'Active'
                ELSE 'Expired'
            END as status,
            COUNT(*) as count
        FROM test.pagination_contexts
        GROUP BY status;
    "

    echo -e "\n${YELLOW}Sessions Active:${NC}"
    $PSQL_CMD -c "
        SELECT COUNT(DISTINCT session_id) as active_sessions
        FROM test.pagination_contexts;
    "

    echo -e "\n${YELLOW}Average Products per Context:${NC}"
    $PSQL_CMD -c "
        SELECT
            ROUND(AVG(total_items), 2) as avg_products,
            MIN(total_items) as min_products,
            MAX(total_items) as max_products
        FROM test.pagination_contexts;
    "

    echo -e "\n${YELLOW}Table Size:${NC}"
    $PSQL_CMD -c "
        SELECT
            pg_size_pretty(pg_total_relation_size('test.pagination_contexts')) as total_size,
            pg_size_pretty(pg_relation_size('test.pagination_contexts')) as table_size,
            pg_size_pretty(pg_indexes_size('test.pagination_contexts')) as indexes_size;
    "
}

# ============================================================================
# Function: View Session Contexts
# ============================================================================
view_session() {
    if [ -z "$1" ]; then
        echo -e "${YELLOW}Usage: ./test_pagination.sh view-session <session_id>${NC}"
        echo -e "${YELLOW}Example: ./test_pagination.sh view-session 12345678-1234-5678-1234-567812345678${NC}"
        return 1
    fi

    SESSION_ID="$1"
    echo -e "${BLUE}📋 Contexts for Session: $SESSION_ID${NC}"

    $PSQL_CMD -c "
        SELECT
            category,
            tool_name,
            query,
            current_page,
            page_size,
            total_items,
            jsonb_array_length(products) as products_count,
            created_at,
            updated_at,
            expires_at - CURRENT_TIMESTAMP as time_until_expiration
        FROM test.pagination_contexts
        WHERE session_id = '$SESSION_ID'
        ORDER BY created_at DESC;
    "
}

# ============================================================================
# Main Script
# ============================================================================
case "${1}" in
    view-all)
        view_all
        ;;
    view-recent)
        view_recent
        ;;
    insert-test)
        insert_test
        ;;
    cleanup)
        cleanup
        ;;
    stats)
        stats
        ;;
    view-session)
        view_session "$2"
        ;;
    *)
        echo -e "${GREEN}Pagination Persistence Testing Script${NC}"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo -e "  ${YELLOW}view-all${NC}              View all pagination contexts"
        echo -e "  ${YELLOW}view-recent${NC}           View 10 most recent contexts"
        echo -e "  ${YELLOW}view-session <id>${NC}    View contexts for specific session"
        echo -e "  ${YELLOW}insert-test${NC}           Insert test data"
        echo -e "  ${YELLOW}cleanup${NC}               Run cleanup function"
        echo -e "  ${YELLOW}stats${NC}                 Show statistics"
        echo ""
        echo "Examples:"
        echo "  $0 view-all"
        echo "  $0 insert-test"
        echo "  $0 view-session 12345678-1234-5678-1234-567812345678"
        echo ""
        ;;
esac