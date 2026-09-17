-- Satu seller harus tepat satu baris
SELECT COUNT(*) = COUNT(DISTINCT seller_id) AS seller_id_is_unique
FROM mart_seller_performance;
