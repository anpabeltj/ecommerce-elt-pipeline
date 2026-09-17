-- Tidak boleh ada order yang hilang karena join kategori.
-- Satu order bisa punya beberapa kategori, jadi total di mart boleh lebih besar, tapi tidak boleh lebih kecil.
SELECT
    (SELECT SUM(total_orders) FROM mart_top_product_categories)
    >=
    (
        SELECT COUNT(DISTINCT oi.order_id)
        FROM olist_order_items_dataset AS oi
        JOIN olist_orders_dataset AS od
            ON od.order_id = oi.order_id
        WHERE od.order_status NOT IN ('canceled', 'unavailable')
    ) AS no_orders_lost_in_categories;
