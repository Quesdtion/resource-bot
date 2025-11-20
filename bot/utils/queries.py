class DBQueries:
    # ===============================
    #         РЕСУРСЫ
    # ===============================

    # Получить свободный ресурс по типу
    GET_FREE_RESOURCE = """
    SELECT *
    FROM resources
    WHERE type = $1 AND status = 'free'
    ORDER BY id
    LIMIT 1;
    """

    # Пометить ресурс как выданный менеджеру
    ISSUE_RESOURCE = """
    UPDATE resources
    SET
        status = 'busy',
        manager_tg_id = $1,
        issue_datetime = NOW(),
        receipt_state = 'new'
    WHERE id = $2;
    """

    # Лог выдачи ресурса
    HISTORY_LOG = """
    INSERT INTO history (datetime, resource_id, manager_tg_id, type, supplier_id, price, action)
    VALUES (NOW(), $1, $2, $3, NULL, NULL, 'issue');
    """

    # Мои ресурсы (ресурсы текущего менеджера)
    MANAGER_RESOURCES = """
    SELECT *
    FROM resources
    WHERE manager_tg_id = $1 AND status = 'busy';
    """

    # Подтвердить срок жизни ресурса
    CONFIRM_LIFETIME = """
    UPDATE resources
    SET
        receipt_state = 'confirmed',
        lifetime_minutes = $1
    WHERE id = $2;
    """

    # ===============================
    #           ПОКУПКИ
    # ===============================

    # Добавление купленного ресурса (без поставщика)
    ADD_PURCHASE = """
    INSERT INTO history (datetime, resource_id, manager_tg_id, type, supplier_id, price, action)
    VALUES (NOW(), NULL, $1, $2, NULL, $3, 'purchase');
    """

    # ===============================
    #          ОТЧЁТЫ АДМИНА
    # ===============================

    REPORT_RESOURCES = """
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE status = 'free') AS free,
        COUNT(*) FILTER (WHERE status = 'busy') AS busy,
        COUNT(*) FILTER (WHERE status = 'expired') AS expired,
        COUNT(*) FILTER (
            WHERE DATE(issue_datetime) = CURRENT_DATE
        ) AS issued_today
    FROM resources;
    """

    REPORT_FINANCE = """
    SELECT
        COUNT(*) AS purchases_today,
        SUM(price) AS total_spent,
        AVG(price) AS avg_price
    FROM history
    WHERE action = 'purchase'
      AND DATE(datetime) = CURRENT_DATE;
    """
