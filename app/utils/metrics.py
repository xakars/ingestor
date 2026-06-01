from prometheus_client import Counter, Gauge, Histogram

rate_limit_total = Counter(
    'rate_limit_checks_total',
    'Total rate limit checks',
    ['user_id', 'endpoint', 'result'],
)

rate_limit_blocked = Counter(
    'rate_limit_blocked_total',
    'Total blocked requests due to rate limit',
    ['user_id', 'endpoint'],
)

# Гистограмма времени проверки
rate_limit_duration = Histogram(
    'rate_limit_check_duration_seconds',
    'Rate limit check duration',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
)
# Gauge для текущего использования
rate_limit_usage = Gauge(
    'rate_limit_current_usage',
    'Current rate limit usage per user',
    ['user_id', 'endpoint'],
)
