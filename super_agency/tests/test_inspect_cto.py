import pytest
import os


@pytest.fixture
def mock_cto_agent_file(tmp_path):
    """
    Creates a mock 'cto_agent.py' file for testing. This fixture is used to avoid
    dependency on the actual file and to test in a controlled environment.
    """
    dir_path = tmp_path / "DIGITAL LABOUR" / "Digital-Labour" / "agents"
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / "cto_agent.py"
    
    # Writing dummy content to the mock file
    sample_content = "\n".join(f"Line {i}" for i in range(1, 281))
    file_path.write_text(sample_content)
    return str(file_path)


@pytest.mark.parametrize("start,end", [(260, 275), (1, 10), (275, 280)])
def test_read_lines_in_range(mock_cto_agent_file, start, end):
    """
    Tests reading a specific range of lines from the 'cto_agent.py' file.
    This is the happy path test with expected range of lines.
    """
    with open(mock_cto_agent_file, 'r') as f:
        result_lines = [line for i, line in enumerate(
            f, 1) if start <= i <= end]
        
    assert len(result_lines) == (end - start + 1), \
        "The number of lines read does not match the expected count."

    assert result_lines[0].strip() == f"Line {start}", \
        f"Expected first line in result to be 'Line {start}', but got '{result_lines[0].strip()}'."

    assert result_lines[-1].strip() == f"Line {end}", \
        f"Expected last line in result to be 'Line {end}', but got '{result_lines[-1].strip()}'."


def test_read_lines_lower_bound_edge(mock_cto_agent_file):
    """
    Tests reading lines when the start line is near the beginning of the file.
    """
    with open(mock_cto_agent_file, 'r') as f:
        result_lines = [line for i, line in enumerate(f, 1) if 0 <= i <= 5]

    assert len(result_lines) == 5, \
        "Edge test for lower bounds failed, expected 5 lines."

    assert result_lines[0].strip() == "Line 1", \
        "Expected first line to be 'Line 1' for lower bound edge test."


def test_read_lines_upper_bound_edge(mock_cto_agent_file):
    """
    Tests reading lines when the end line exceeds the number of lines in the file.
    """
    with open(mock_cto_agent_file, 'r') as f:
        result_lines = [line for i, line in enumerate(f, 1) if 275 <= i <= 300]

    assert len(result_lines) == 6, \
        "Edge test for upper bounds failed, expected 6 available lines."


def test_empty_file_scenario(tmp_path):
    """
    Tests the behavior when reading from an entirely empty cto_agent.py file.
    Verifies that no lines are returned, and no error is thrown.
    """
    dir_path = tmp_path / "DIGITAL LABOUR" / "Digital-Labour" / "agents"
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / "cto_agent.py"
    file_path.write_text("")  # Create an empty file

    with open(file_path, 'r') as f:
        result_lines = [line for i, line in enumerate(f, 1) if 260 <= i <= 275]

    assert len(result_lines) == 0, \
        "Expected no lines to be read from an empty file."


def test_non_existent_file():
    """
    Tests the behavior of the script when the file does not exist.
    Ensures that the appropriate exception is raised.
    """
    with pytest.raises(FileNotFoundError, match=r".*No such file or directory.*"):
        with open('non_existent_file.py', 'r') as f:
            pass  # Code should not reach this point
