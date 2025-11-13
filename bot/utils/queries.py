class DBQueries:
    GET_MANAGER = "SELECT * FROM managers WHERE tg_id=$1"

    GET_FREE_RESOURCE = """
    SELECT * FROM resources
    WHERE type=$1 AND status='free'
    ORDER BY id
    LIMIT 1
    """

    ISSUE_RESOURCE = """
    UPDATE resources
    SET status='issued',
        manager_tg_id=$1,
        issue_datetime=NOW()
    WHERE id=$2
    """

    SET_RECEIPT_STATE = """
    UPDATE resources
    SET receipt_state=$1,
        status=$2
    WHERE id=$3
    """

    HISTORY_LOG = """
    INSERT INTO history(resource_id, manager_tg_id, type, supplier_id, price, action, receipt_state, lifetime_minutes)
    VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
    """

    REPORT_GLOBAL_TYPES = """
    SELECT type,
           COUNT(*) AS total,
           SUM(CASE WHEN receipt_state='working' THEN 1 END) AS working,
           SUM(CASE WHEN receipt_state='blocked' THEN 1 END) AS blocked,
           SUM(CASE WHEN receipt_state='error' THEN 1 END) AS errors,
           AVG(lifetime_minutes) AS avg_lifetime,
           AVG(price) AS avg_price,
           SUM(price) AS total_cost
    FROM history
    WHERE DATE(datetime)=CURRENT_DATE
    GROUP BY type
    ORDER BY type;
    """

    REPORT_MANAGER = """
    SELECT type,
           COUNT(*) AS total,
           SUM(CASE WHEN receipt_state='working' THEN 1 END) AS working,
           SUM(CASE WHEN receipt_state='blocked' THEN 1 END) AS blocked,
           AVG(price) AS avg_price,
           AVG(lifetime_minutes) AS avg_lifetime,
           SUM(price) AS total_cost
    FROM history
    WHERE DATE(datetime)=CURRENT_DATE
      AND manager_tg_id=$1
    GROUP BY type
    ORDER BY type;
    """

    REPORT_FINANCE = """
    SELECT supplier_id,
           type,
           COUNT(*) AS total,
           SUM(price) AS spent,
           AVG(price) AS avg_price
    FROM history
    WHERE DATE(datetime)=CURRENT_DATE
    GROUP BY supplier_id, type
    ORDER BY supplier_id, type;
    """
