-- Rata rata review harus di antara 1 dan 5 (NULL diperbolehkan untuk seller tanpa review)
SELECT COUNT(*) = 0 AS review_score_in_range
FROM mart_seller_performance
WHERE average_review_score < 1
   OR average_review_score > 5;