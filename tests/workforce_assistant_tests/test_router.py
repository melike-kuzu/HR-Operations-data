from workforce_assistant.domain.models import RouteType
from workforce_assistant.routing.router import route_question


def test_bench_routes_to_bench():
    assert route_question("Who is on bench?").route_type == RouteType.BENCH


def test_skill_routes_to_skill_lookup():
    assert (
        route_question("Who knows Azure?")
        .route_type
        == RouteType.SKILL_LOOKUP
    )


def test_policy_routes_to_document_search():
    assert (
        route_question("What does the leave policy say?")
        .route_type
        == RouteType.DOCUMENT_SEARCH
    )

def test_profile_experience_with_azure_routes_to_profile_search():
    decision = route_question("Show profile experience in Azure")

    assert decision.route_type == RouteType.PROFILE_SEARCH


def test_who_knows_azure_routes_to_skill_lookup():
    decision = route_question("Who knows Azure?")

    assert decision.route_type == RouteType.SKILL_LOOKUP


def test_azure_policy_routes_to_document_search():
    decision = route_question("What does the Azure policy document say?")

    assert decision.route_type == RouteType.DOCUMENT_SEARCH