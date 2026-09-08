from src.main import update_error_state


def test_new_error_is_saved_and_reported(tmp_path) -> None:
    state_file = tmp_path / "last-error.log"

    assert update_error_state("new error", state_file)
    assert state_file.read_text() == "new error"


def test_repeated_error_is_not_reported(tmp_path) -> None:
    state_file = tmp_path / "last-error.log"
    state_file.write_text("same error")

    assert not update_error_state("same error", state_file)
    assert state_file.read_text() == "same error"


def test_success_clears_previous_error(tmp_path) -> None:
    state_file = tmp_path / "last-error.log"
    state_file.write_text("old error")

    assert not update_error_state("", state_file)
    assert state_file.read_text() == ""


def test_recurrence_after_success_is_reported(tmp_path) -> None:
    state_file = tmp_path / "last-error.log"
    state_file.write_text("recurring error")
    update_error_state("", state_file)

    assert update_error_state("recurring error", state_file)
