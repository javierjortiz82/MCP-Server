-- ============================================================================
-- BOOKING FUNCTIONS - Appointment management and availability checking
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION test.update_booking_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for appointments
DROP TRIGGER IF EXISTS trg_update_appointments_timestamp ON test.appointments;
CREATE TRIGGER trg_update_appointments_timestamp
    BEFORE UPDATE ON test.appointments
    FOR EACH ROW
    EXECUTE FUNCTION test.update_booking_timestamp();

-- Trigger for service_types
DROP TRIGGER IF EXISTS trg_update_service_types_timestamp ON test.service_types;
CREATE TRIGGER trg_update_service_types_timestamp
    BEFORE UPDATE ON test.service_types
    FOR EACH ROW
    EXECUTE FUNCTION test.update_booking_timestamp();

-- Trigger for business_hours
DROP TRIGGER IF EXISTS trg_update_business_hours_timestamp ON test.business_hours;
CREATE TRIGGER trg_update_business_hours_timestamp
    BEFORE UPDATE ON test.business_hours
    FOR EACH ROW
    EXECUTE FUNCTION test.update_booking_timestamp();

-- Trigger for blocked_times
DROP TRIGGER IF EXISTS trg_update_blocked_times_timestamp ON test.blocked_times;
CREATE TRIGGER trg_update_blocked_times_timestamp
    BEFORE UPDATE ON test.blocked_times
    FOR EACH ROW
    EXECUTE FUNCTION test.update_booking_timestamp();

-- Trigger for service_hours
DROP TRIGGER IF EXISTS trg_update_service_hours_timestamp ON test.service_hours;
CREATE TRIGGER trg_update_service_hours_timestamp
    BEFORE UPDATE ON test.service_hours
    FOR EACH ROW
    EXECUTE FUNCTION test.update_booking_timestamp();

-- ============================================================================
-- Function: is_slot_available() - Check availability with hybrid scheduling
-- ============================================================================
-- HYBRID SCHEDULING: Supports service-specific hours with fallback to business_hours
CREATE OR REPLACE FUNCTION test.is_slot_available(
    p_booking_date DATE,
    p_booking_time TIME,
    p_duration_minutes INTEGER,
    p_service_type VARCHAR DEFAULT NULL  -- Optional service-specific scheduling
) RETURNS BOOLEAN AS $$
DECLARE
    v_end_time TIME;
    v_day_of_week INTEGER;
    v_open_time TIME;
    v_close_time TIME;
    v_hours_exist BOOLEAN;
BEGIN
    -- Calculate end time
    v_end_time := p_booking_time + (p_duration_minutes || ' minutes')::INTERVAL;

    -- Get day of week (0=Monday, 6=Sunday)
    v_day_of_week := EXTRACT(DOW FROM p_booking_date)::INTEGER;
    -- Adjust: PostgreSQL DOW is 0=Sunday, we need 0=Monday
    v_day_of_week := CASE WHEN v_day_of_week = 0 THEN 6 ELSE v_day_of_week - 1 END;

    -- HYBRID SCHEDULING LOGIC:
    -- Step 1: Try to get service-specific hours if service_type provided
    v_hours_exist := false;
    IF p_service_type IS NOT NULL THEN
        SELECT INTO v_open_time, v_close_time, v_hours_exist
            sh.open_time, sh.close_time, true
        FROM test.service_hours sh
        JOIN test.service_types st ON sh.service_type_id = st.id
        WHERE st.name = p_service_type
        AND sh.day_of_week = v_day_of_week
        AND sh.active = true
        ORDER BY sh.priority ASC
        LIMIT 1;
    END IF;

    -- Step 2: If no service-specific hours, fall back to business_hours
    IF NOT v_hours_exist THEN
        SELECT INTO v_open_time, v_close_time
            open_time, close_time
        FROM test.business_hours
        WHERE day_of_week = v_day_of_week
        AND active = true;
    END IF;

    -- Check if we found valid hours
    IF v_open_time IS NULL OR v_close_time IS NULL THEN
        RETURN false;  -- Business closed this day
    END IF;

    -- Check if booking fits within operating hours
    IF NOT (v_open_time <= p_booking_time AND v_close_time >= v_end_time) THEN
        RETURN false;
    END IF;

    -- Check blocked times (full day)
    IF EXISTS (
        SELECT 1 FROM test.blocked_times
        WHERE block_date = p_booking_date
        AND is_full_day = true
    ) THEN
        RETURN false;
    END IF;

    -- Check blocked times (specific time range)
    IF EXISTS (
        SELECT 1 FROM test.blocked_times
        WHERE block_date = p_booking_date
        AND is_full_day = false
        AND (
            (p_booking_time >= start_time AND p_booking_time < end_time) OR
            (v_end_time > start_time AND v_end_time <= end_time) OR
            (p_booking_time <= start_time AND v_end_time >= end_time)
        )
    ) THEN
        RETURN false;
    END IF;

    -- Check existing appointments
    IF EXISTS (
        SELECT 1 FROM test.appointments
        WHERE booking_date = p_booking_date
        AND status IN ('confirmed', 'rescheduled')
        AND (
            (booking_time >= p_booking_time AND booking_time < v_end_time) OR
            ((booking_time + (duration_minutes || ' minutes')::INTERVAL) > p_booking_time
             AND (booking_time + (duration_minutes || ' minutes')::INTERVAL) <= v_end_time) OR
            (booking_time <= p_booking_time AND
             (booking_time + (duration_minutes || ' minutes')::INTERVAL) >= v_end_time)
        )
    ) THEN
        RETURN false;
    END IF;

    RETURN true;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- Function: cleanup_old_appointments() - Maintenance function
-- ============================================================================
CREATE OR REPLACE FUNCTION test.cleanup_old_appointments(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM test.appointments
    WHERE status IN ('completed', 'cancelled', 'no_show')
    AND (
        (completed_at IS NOT NULL AND completed_at < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL) OR
        (cancelled_at IS NOT NULL AND cancelled_at < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL)
    );

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT EXECUTE ON FUNCTION test.is_slot_available(DATE, TIME, INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION test.is_slot_available(DATE, TIME, INTEGER, VARCHAR) TO mcp_user;
GRANT EXECUTE ON FUNCTION test.cleanup_old_appointments(INTEGER) TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Booking functions created:';
    RAISE NOTICE '   - update_booking_timestamp() with triggers';
    RAISE NOTICE '   - is_slot_available() with hybrid scheduling';
    RAISE NOTICE '   - cleanup_old_appointments() maintenance';
END $$;
