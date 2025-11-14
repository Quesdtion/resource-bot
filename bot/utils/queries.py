class DBQueries:
    # --------------------- ПРОВЕРКА/СОЗДАНИЕ ТАБЛИЦ ---------------------

    CREATE_MANAGERS = """
    CREATE TABLE IF NOT EXISTS managers (
        id SERIAL PRIMARY KEY,
        tg_id BIGINT UNIQUE NOT NULL,
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
        buy_price NUMERIC DEFAULT 0,
        status TEXT DEFAULT 'free',
        manager_tg_id BIGINT,
        lifetime INT DEFAULT 0
    );
    """

    CREATE_HISTORY = """
    CREATE TABLE IF NOT EXISTS history (
        id SERIAL PRIMARY KEY,
        resource_id INT,
        manager_tg_id BIGINT,
        type TEXT,
        price NUMERIC,
        datetime TIMESTAMP DEFAULT NOW()
    );
    """

    # --------------------- ОТЧЁТЫ ---------------------

    # Ежедневный отчёт
    REPORT_DAILY = """
    SELECT type,
           COUNT(*) FILTER (WHERE status = 'busy') AS issued,
           COUNT(*) FILTER (WHERE status = 'closed') AS closed
    FROM resources
    GROUP BY type
    ORDER BY type;
    """

    # Отчёт по менеджерам
    REPORT_MANAGER = """
    SELECT manager_tg_id,
           COUNT(*) AS total
    FROM history
    WHERE DATE(datetime) = CURRENT_DATE
    GROUP BY manager_tg_id
    ORDER BY total DESC;
    """

    # Финансовый отчёт (без поставщиков!)
    REPORT_FINANCE = """
    SELECT type,
           COUNT(*) AS total,
           SUM(price) AS spent,
           AVG(price) AS avg_price
    FROM history
    WHERE DATE(datetime) = CURRENT_DATE
    GROUP BY type
    ORDER BY type;
    """

    # --------------------- РАБОТА С РЕСУРСАМИ ---------------------

    GET_FREE_RESOURCE = """
    SELECT * FROM resources
    WHERE type = $1 AND status = 'free'
    ORDER BY id
    LIMIT 1;
    """

    SET_RESOURCE_BUSY = """
    UPDATE resources
    SET status = 'busy',
        manager_tg_id = $2,
        lifetime = $3
    WHERE id = $1;
    """

    SET_RESOURCE_CLOSED = """
    UPDATE resources
    SET status = 'closed'
    WHERE id = $1;
    """

    INSERT_HISTORY = """
    INSERT INTO history (resource_id, manager_tg_id, type, price)
    VALUES ($1, $2, $3, $4);
    """

    # --------------------- МЕНЕДЖЕРЫ ---------------------

    ADD_MANAGER = """
    INSERT INTO managers (tg_id, name, role)
    VALUES ($1, $2, $3)
    ON CONFLICT (tg_id) DO NOTHING;
    """

    GET_MANAGER_ROLE = """
    SELECT role FROM managers WHERE tg_id = $1;
    """

    # --------------------- ДОБАВЛЕНИЕ РЕСУРСОВ ---------------------

    ADD_RESOURCE = """
    INSERT INTO resources (type, login, password, buy_price)
    VALUES ($1, $2, $3, $4);
    """

    # Массовое добавление (для add_batch)
    ADD_RESOURCE_BATCH = """
    INSERT INTO resources (type, buy_price)
    VALUES ($1, $2)
    RETURNING id;
    """
