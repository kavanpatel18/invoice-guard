from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_app_boots_and_has_main_tabs():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    labels = [t.label for t in at.tabs]
    for want in ("Dashboard", "Process an invoice", "Human review queue", "Evaluation", "Architecture"):
        assert any(want in l for l in labels), want


def test_run_agents_button_executes_workflow_with_fault():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox[0].select(next(o for o in at.selectbox[0].options if "Persistent" in o))  # fault injection
    at.button[0].click().run()
    assert not at.exception
    case = at.session_state["case"]
    assert case.attempts in (1, 2) and case.decision["decision"]
