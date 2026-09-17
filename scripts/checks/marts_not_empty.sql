-- Semua mart harus punya data
SELECT
    (SELECT COUNT(*) FROM mart_revenue_by_month) > 0 AS revenue_by_month_has_rows,
    (SELECT COUNT(*) FROM mart_top_product_categories) > 0 AS top_categories_has_rows,
    (SELECT COUNT(*) FROM mart_seller_performance) > 0 AS seller_performance_has_rows;
