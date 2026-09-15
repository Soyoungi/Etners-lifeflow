"""서비스별 개인화 조건(ServiceRule)을 평가해 노출 여부/상태를 결정한다."""

NUMERIC_FIELDS = {"tenure_years", "children_count", "min_child_age", "max_child_age"}
BOOLEAN_FIELDS = {
    "is_new_hire",
    "is_team_leader",
    "is_officer",
    "has_family",
    "has_spouse",
    "has_children",
}


def _coerce(field, raw_value):
    if field in NUMERIC_FIELDS:
        return float(raw_value)
    if field in BOOLEAN_FIELDS:
        return str(raw_value).strip().lower() in ("true", "1", "y", "yes")
    return raw_value


def _eval_single(rule, context):
    actual = context.get(rule.field)

    if rule.operator == "exists":
        expected_bool = str(rule.value).strip().lower() in ("true", "1", "y", "yes")
        return bool(actual) == expected_bool

    if actual is None:
        return False

    if rule.operator == "in":
        options = [v.strip() for v in rule.value.split(",")]
        return str(actual) in options
    if rule.operator == "not_in":
        options = [v.strip() for v in rule.value.split(",")]
        return str(actual) not in options

    expected = _coerce(rule.field, rule.value)

    if rule.operator == "=":
        return str(actual) == str(expected) if not isinstance(expected, (int, float)) else actual == expected
    if rule.operator == "!=":
        return str(actual) != str(expected) if not isinstance(expected, (int, float)) else actual != expected
    if rule.operator == ">=":
        return actual >= expected
    if rule.operator == "<=":
        return actual <= expected
    if rule.operator == ">":
        return actual > expected
    if rule.operator == "<":
        return actual < expected

    raise ValueError(f"지원하지 않는 operator: {rule.operator}")


def evaluate(service, context):
    """서비스에 연결된 규칙을 순서대로 평가해 최종 대상 여부(bool)를 반환한다.

    규칙이 없으면 전체 임직원 대상(True)으로 간주한다.
    """
    rules = service.rules
    if not rules:
        return True

    result = _eval_single(rules[0], context)
    for prev_rule, rule in zip(rules, rules[1:]):
        current = _eval_single(rule, context)
        if prev_rule.logical_operator == "OR":
            result = result or current
        else:
            result = result and current
    return result


# 신청 진행 중(대기)으로 취급하는 신청서 상태
PENDING_APPLICATION_STATUSES = {"SUBMITTED", "RECEIVED", "REVIEWING", "SUPPLEMENT_REQUIRED"}


def resolve_status(service, context, latest_application=None):
    """작업지시서 10번 섹션의 서비스 상태를 산출한다."""
    if latest_application is not None:
        if latest_application.status in PENDING_APPLICATION_STATUSES:
            return "APPLIED"
        if latest_application.status == "APPROVED":
            return "IN_PROGRESS"
        if latest_application.status == "COMPLETED":
            return "COMPLETED"
        # REJECTED는 재신청 가능하도록 아래 일반 판정으로 넘어간다.

    eligible = evaluate(service, context)
    if not eligible:
        return "NOT_AVAILABLE"
    if service.application_expired():
        return "EXPIRED"
    if service.application_window_open():
        return "APPLY_AVAILABLE"
    return "AVAILABLE"


STATUS_META = {
    "AVAILABLE": {"emoji": "🟢", "label": "이용 가능", "css": "status-available"},
    "APPLY_AVAILABLE": {"emoji": "🟡", "label": "신청 가능", "css": "status-apply"},
    "APPLIED": {"emoji": "🔵", "label": "신청 완료", "css": "status-applied"},
    "IN_PROGRESS": {"emoji": "🔵", "label": "처리 중", "css": "status-applied"},
    "NOT_AVAILABLE": {"emoji": "⚪", "label": "이용 불가", "css": "status-unavailable"},
    "COMPLETED": {"emoji": "🔵", "label": "처리 완료", "css": "status-applied"},
    "EXPIRED": {"emoji": "🔴", "label": "기간 만료", "css": "status-expired"},
}
