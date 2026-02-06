"""
Tests for CLI functionality.
"""

import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli import load_prompts_from_file, create_parser


class TestLoadPromptsFromFile:
    """Tests for load_prompts_from_file function."""
    
    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_prompts_from_file("nonexistent.txt")
    
    def test_load_valid_prompts(self, tmp_path):
        """Test loading valid prompts from file."""
        prompts_file = tmp_path / "prompts.txt"
        prompts_file.write_text("Prompt 1\nPrompt 2\nPrompt 3\n")
        
        prompts = load_prompts_from_file(str(prompts_file))
        assert len(prompts) == 3
        assert prompts[0] == "Prompt 1"
        assert prompts[1] == "Prompt 2"
        assert prompts[2] == "Prompt 3"
    
    def test_skip_comments(self, tmp_path):
        """Test that comments are skipped."""
        prompts_file = tmp_path / "prompts.txt"
        prompts_file.write_text("# Comment\nPrompt 1\n# Another comment\nPrompt 2\n")
        
        prompts = load_prompts_from_file(str(prompts_file))
        assert len(prompts) == 2
        assert prompts[0] == "Prompt 1"
        assert prompts[1] == "Prompt 2"
    
    def test_skip_empty_lines(self, tmp_path):
        """Test that empty lines are skipped."""
        prompts_file = tmp_path / "prompts.txt"
        prompts_file.write_text("Prompt 1\n\nPrompt 2\n\n\nPrompt 3\n")
        
        prompts = load_prompts_from_file(str(prompts_file))
        assert len(prompts) == 3
    
    def test_strip_whitespace(self, tmp_path):
        """Test that whitespace is stripped."""
        prompts_file = tmp_path / "prompts.txt"
        prompts_file.write_text("  Prompt 1  \n\tPrompt 2\t\n")
        
        prompts = load_prompts_from_file(str(prompts_file))
        assert prompts[0] == "Prompt 1"
        assert prompts[1] == "Prompt 2"


class TestCreateParser:
    """Tests for create_parser function."""
    
    def test_parser_exists(self):
        """Test that parser can be created."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "release_flow"
    
    def test_required_arguments(self):
        """Test that required arguments are enforced."""
        parser = create_parser()
        
        # Missing --repo should fail
        with pytest.raises(SystemExit):
            parser.parse_args([])
        
        # Missing mode (--prompt or --continuous) should fail
        with pytest.raises(SystemExit):
            parser.parse_args(["--repo", "owner/repo"])
    
    def test_valid_single_prompt(self):
        """Test parsing valid single prompt arguments."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "owner/repo",
            "--prompt", "Fix bugs"
        ])
        
        assert args.repo == "owner/repo"
        assert args.prompt == "Fix bugs"
        assert args.continuous is False
    
    def test_valid_continuous(self):
        """Test parsing valid continuous mode arguments."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "owner/repo",
            "--continuous"
        ])
        
        assert args.repo == "owner/repo"
        assert args.continuous is True
        assert args.prompt is None
    
    def test_optional_arguments(self):
        """Test parsing optional arguments."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "owner/repo",
            "--prompt", "Fix bugs",
            "--auto-merge",
            "--iterations", "5",
            "--delay", "60",
            "--timeout", "600",
        ])
        
        assert args.auto_merge is True
        assert args.iterations == 5
        assert args.delay == 60
        assert args.timeout == 600
    
    def test_merge_method_choices(self):
        """Test that merge method is restricted to valid choices."""
        parser = create_parser()
        
        # Valid merge method
        args = parser.parse_args([
            "--repo", "owner/repo",
            "--prompt", "Fix bugs",
            "--merge-method", "rebase"
        ])
        assert args.merge_method == "rebase"
        
        # Invalid merge method should fail
        with pytest.raises(SystemExit):
            parser.parse_args([
                "--repo", "owner/repo",
                "--prompt", "Fix bugs",
                "--merge-method", "invalid"
            ])
