-- Pertanyaan: Bagaimana tren revenue bulanan, dan berapa pertumbuhannya dibanding bulan sebelumnya?
-- Data sebelum 2017 dan setelah Agustus 2018 sangat sedikit, jadi tidak ditampilkan agar tren tidak menyesatkan.
SELECT
    date AS month,
    total_revenue,
    ROUND(
        (total_revenue - LAG(total_revenue) OVER (ORDER BY date))
        / NULLIF(LAG(total_revenue) OVER (ORDER BY date), 0) * 100,
        1
    ) AS growth_pct
FROM mart_revenue_by_month
WHERE date >= DATE '2017-01-01'
  AND date < DATE '2018-09-01'
ORDER BY month
