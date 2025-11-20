class DBQueries:
    # ===========================
    #        МЕНЕДЖЕРЫ
    # ===========================

    CHECK_MANAGER_ROLE = """
    SELECT role FROM managers WHERE tg_id = $1;
    """

    GET_FREE_RESOURCE_BY_TYPE = """
    SELECT *
    FROM resources
    WHERE type = $1 AND status = 'free'
    ORDER BY id ASC
    LIMIT 1;
    """

    ISSUE_RESOURCE = """
    UPDATE resources
    SET status = 'busy',
        manager_tg_id = $1,
        issue_datetime = NOW(),
        receipt_state = 'new'
    WHERE id = $2;
    """

    HISTORY_LOG = """
    INSERT INTO history (datetime, resource_id, manager_tg_id, type, action, price)
    VALUES (NOW(), $1, $2, $3, 'issued', NULL);
    """

    # ===========================
    #     СРОК ЖИЗНИ / ЛАЙФТАЙМ
    # ===========================

    SET_LIFETIME = """
    UPDATE resources
    SET lifetime_minutes = $1,
        receipt_state = 'used',
        end_datetime = NOW()
    WHERE id = $2 AND manager_tg_id = $3;
    """

    HISTORY_LIFETIME = """
    INSERT INTO history (datetime, resource_id, manager_tg_id, type, action, lifetime_minutes)
    VALUES (NOW(), $1, $2, $3, 'lifetime_set', $4);
    """

    GET_ISSUED_RESOURCES = """
    SELECT *
    FROM resources
    WHERE manager_tg_id = $1 AND status = 'busy';
    """

    # ===========================
    #       АДМИН – ОТЧЁТЫ
    # ===========================

    REPORT_RESOURCES = """
    SELECT
        (SELECT COUNT(*) FROM resources) AS total,
        (SELECT COUNT(*) FROM resources WHERE status = 'free') AS free,
        (SELECT COUNT(*) FROM resources WHERE status = 'busy') AS busy,
        (SELECT COUNT(*) FROM resources WHERE receipt_state = 'used' AND end_datetime::date = NOW()::date) AS expired_today,
        (SELECT COUNT(*) FROM history WHERE action = 'issued' AND datetime::date = NOW()::date) AS issued_today;
    """

    REPORT_FINANCE = """
    SELECT
        COALESCE(SUM(price), 0) AS total_purchase_cost
    FROM history
    WHERE action = 'purchase'
      AND datetime::date = NOW()::date;
    """

    # ===========================
    #     АДМИН – ВЫГРУЗКА/ЗАГРУЗКА
    # ===========================

    INSERT_RESOURCE_BULK = """
    INSERT INTO resources (type, login, password, proxy, buy_price, status)
    VALUES ($1, $2, $3, $4, $5, 'free');
    """

    INSERT_PURCHASE_LOG = """
    INSERT INTO history (datetime, resource_id, manager_tg_id, type, action, price)
    VALUES (NOW(), $1, NULL, $2, 'purchase', $3);
    """

    # ===========================
    #        ПРОЧЕЕ
    # ===========================

    GET_MANAGER = """
    SELECT * FROM managers WHERE tg_id = $1;
    """

    GET_RESOURCE_BY_ID = """
    SELECT * FROM resources WHERE id = $1;
    """
