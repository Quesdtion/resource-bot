class DBQueries:
    # ===========================
    #        МЕНЕДЖЕРЫ / РОЛИ
    # ===========================

    CHECK_MANAGER_ROLE = """
    SELECT role FROM managers WHERE tg_id = $1;
    """

    GET_MANAGER = """
    SELECT * FROM managers WHERE tg_id = $1;
    """

    # ===========================
    #        РЕСУРСЫ
    # ===========================

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

    GET_ISSUED_RESOURCES = """
    SELECT *
    FROM resources
    WHERE manager_tg_id = $1 AND status = 'busy';
    """

    GET_RESOURCE_BY_ID = """
    SELECT *
    FROM resources
    WHERE id = $1;
    """

    # ===========================
    #      ОТМЕТКА СТАТУСА
    #   (receipt_state: good/bad)
    # ===========================

    MARK_RESOURCE_GOOD = """
    UPDATE resources
    SET receipt_state = 'good'
    WHERE id = $1 AND manager_tg_id = $2;
    """

    MARK_RESOURCE_BAD = """
    UPDATE resources
    SET receipt_state = 'bad'
    WHERE id = $1 AND manager_tg_id = $2;
    """

    # ===========================
    #        ЛАЙФТАЙМ
    # ===========================

    SET_LIFETIME = """
    UPDATE resources
    SET lifetime_minutes = $1,
        receipt_state = 'used',
        end_datetime = NOW()
    WHERE id = $2 AND manager_tg_id = $3;
    """

    HISTORY_LIFETIME = """
    INSERT INTO history (
        datetime,
        resource_id,
        manager_tg_id,
        type,
        action,
        lifetime_minutes
    )
    VALUES (NOW(), $1, $2, $3, 'lifetime_set', $4);
    """

    # ===========================
    #           ИСТОРИЯ
    # ===========================

    HISTORY_LOG = """
    INSERT INTO history (
        datetime,
        resource_id,
        manager_tg_id,
        type,
        action,
        price
    )
    VALUES (NOW(), $1, $2, $3, 'issued', NULL);
    """

    HISTORY_STATUS_CHANGE = """
    INSERT INTO history (
        datetime,
        resource_id,
        manager_tg_id,
        type,
        action,
        price
    )
    VALUES (NOW(), $1, $2, $3, $4, NULL);
    """

    INSERT_PURCHASE_LOG = """
    INSERT INTO history (
        datetime,
        resource_id,
        manager_tg_id,
        type,
        action,
        price
    )
    VALUES (NOW(), $1, NULL, $2, 'purchase', $3);
    """

    # ===========================
    #       ОТЧЁТЫ АДМИНА
    # ===========================

    REPORT_RESOURCES = """
    SELECT
        (SELECT COUNT(*) FROM resources) AS total,
        (SELECT COUNT(*) FROM resources WHERE status = 'free') AS free,
        (SELECT COUNT(*) FROM resources WHERE status = 'busy') AS busy,
        (SELECT COUNT(*) FROM resources
            WHERE receipt_state = 'used'
              AND end_datetime::date = NOW()::date) AS expired_today,
        (SELECT COUNT(*) FROM history
            WHERE action = 'issued'
              AND datetime::date = NOW()::date) AS issued_today;
    """

    REPORT_FINANCE = """
    SELECT
        COALESCE(SUM(price), 0) AS total_purchase_cost
    FROM history
    WHERE action = 'purchase'
      AND datetime::date = NOW()::date;
    """

    # ===========================
    #     ЗАГРУЗКА РЕСУРСОВ
    # ===========================

    INSERT_RESOURCE_BULK = """
    INSERT INTO resources (type, login, password, proxy, buy_price, status)
    VALUES ($1, $2, $3, $4, $5, 'free');
    """
