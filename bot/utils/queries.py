class DBQueries:
    # --------------------- СОЗДАНИЕ ТАБЛИЦ (на всякий случай) ---------------------

    CREATE_MANAGERS = """
    CREATE TABLE IF NOT EXISTS managers (
        tg_id BIGINT PRIMARY KEY,
        name TEXT,
        role TEXT DEFAULT 'manager'
    );
    """

    CREATE_RESOURCES = """
    CREATE TABLE IF NOT EXISTS resources (
        id SERIAL PRIMARY KEY,
        type TEXT NOT NULL,
        login TEXT,
        password TEXT,
        proxy TEXT,
        supplier_id INT,
        buy_price NUMERIC DEFAULT 0,
        status TEXT,
        manager_tg_id BIGINT,
        issue_datetime TIMESTAMP,
        receipt_state TEXT,
        lifetime_minutes INT,
        end_datetime TIMESTAMP
    );
    """

    CREATE_HISTORY = """
    CREATE TABLE IF NOT EXISTS history (
        id SERIAL PRIMARY KEY,
        datetime TIMESTAMP DEFAULT NOW(),
        resource_id INT,
        manager_tg_id BIGINT,
        type TEXT,
        supplier_id INT,
        price NUMERIC,
        action TEXT,
        receipt_state TEXT,
        lifetime_minutes INT
    );
    """

    # --------------------- ОТЧЁТЫ ---------------------

    # Ежедневный отчёт по типам ресурсов (по состоянию таблицы resources)
    REPORT_DAILY = """
    SELECT type,
           COUNT(*) FILTER (WHERE manager_tg_id IS NOT NULL) AS issued,
           COUNT(*) FILTER (WHERE end_datetime IS NOT NULL)  AS closed
    FROM resources
    GROUP BY type
    ORDER BY type;
    """

    # Отчёт по менеджерам за сегодня (по истории)
    REPORT_MANAGER = """
    SELECT manager_tg_id,
           COUNT(*) AS total
    FROM history
    WHERE DATE(datetime) = CURRENT_DATE
    GROUP BY manager_tg_id
    ORDER BY total DESC;
    """

    # Финансовый отчёт за сегодня (без поставщиков, только типы ресурсов)
    REPORT_FINANCE = """
    SELECT type,
           COUNT(*)              AS total_operations,
           SUM(price)            AS total_spent,
           AVG(price)            AS avg_price
    FROM history
    WHERE DATE(datetime) = CURRENT_DATE
    GROUP BY type
    ORDER BY type;
    """

    # --------------------- РАБОТА С РЕСУРСАМИ ---------------------

    # Найти свободный ресурс нужного типа:
    # статус = 'free' И ещё не привязан к менеджеру
    GET_FREE_RESOURCE = """
    SELECT *
    FROM resources
    WHERE type = $1
      AND status = 'free'
      AND manager_tg_id IS NULL
    ORDER BY id
    LIMIT 1;
    """

    # Пометить ресурс выданным менеджеру
    # status НЕ трогаем, чтобы не нарушать resources_status_check
    ISSUE_RESOURCE = """
    UPDATE resources
    SET manager_tg_id   = $1,
        issue_datetime  = NOW(),
        receipt_state   = 'new'
    WHERE id = $2;
    """

    # Закрыть ресурс (без изменения status)
    CLOSE_RESOURCE = """
    UPDATE resources
    SET end_datetime = NOW()
    WHERE id = $1;
    """

    # Записать действие в историю
    INSERT_HISTORY = """
    INSERT INTO history (
        resource_id,
        manager_tg_id,
        type,
        supplier_id,
        price,
        action,
        receipt_state,
        lifetime_minutes
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
    """

    # --------------------- МЕНЕДЖЕРЫ ---------------------

    ADD_MANAGER = """
    INSERT INTO managers (tg_id, name, role)
    VALUES ($1, $2, $3)
    ON CONFLICT (tg_id) DO NOTHING;
    """

    GET_MANAGER_ROLE = """
    SELECT role FROM managers
    WHERE tg_id = $1;
    """

    # --------------------- ДОБАВЛЕНИЕ РЕСУРСОВ ---------------------

    # Добавление одного ресурса
    ADD_RESOURCE = """
    INSERT INTO resources (
        type,
        login,
        password,
        proxy,
        supplier_id,
        buy_price,
        status
    )
    VALUES ($1, $2, $3, $4, $5, $6, 'free');
    """
