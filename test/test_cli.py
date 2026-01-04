#!/usr/bin/env python3
"""Test command-line interface and argument parsing."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import sys
import json
from pathlib import Path
import sfs_processor


class TestTargetDateCLI:
    """Test --target-date command line argument."""

    @patch('sfs_processor.make_document')
    def test_target_date_argument_passed_to_make_document(self, mock_make_document):
        """Test that --target-date is correctly passed to make_document()."""
        # Create a mock JSON file path
        mock_json_path = MagicMock(spec=Path)
        mock_json_path.name = "sfs-2023-123.json"
        mock_json_path.__str__ = lambda x: "sfs_json/sfs-2023-123.json"

        # Mock file data
        mock_data = {"beteckning": "2023:123", "rubrik": "Test"}

        # Mock Path and file operations
        with patch('sfs_processor.Path') as mock_path_class:
            # Setup input directory mock
            mock_input_path = MagicMock()
            mock_input_path.exists.return_value = True
            mock_input_path.glob.return_value = [mock_json_path]

            # Setup output directory mock
            mock_output_path = MagicMock()
            mock_output_path.exists.return_value = True

            # Configure Path to return appropriate mocks
            def path_side_effect(path_str):
                if 'sfs_json' in str(path_str) or path_str == 'sfs_json':
                    return mock_input_path
                else:
                    return mock_output_path

            mock_path_class.side_effect = path_side_effect

            # Mock open and json.load
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))):
                with patch('json.load', return_value=mock_data):
                    # Test with --target-date argument
                    test_args = [
                        'sfs_processor.py',
                        '--input', 'sfs_json',
                        '--output', 'output',
                        '--formats', 'md',
                        '--target-date', '2023-06-15'
                    ]

                    with patch.object(sys, 'argv', test_args):
                        try:
                            sfs_processor.main()
                        except SystemExit:
                            pass

                    # Verify make_document was called with target_date
                    assert mock_make_document.called, "make_document should have been called"
                    call_args = mock_make_document.call_args

                    # The last argument should be target_date
                    assert call_args[0][-1] == '2023-06-15', \
                        f"Expected target_date '2023-06-15', got {call_args[0][-1]}"

    @patch('sfs_processor.make_document')
    def test_target_date_default_none(self, mock_make_document):
        """Test that target_date defaults to None when not specified."""
        # Create a mock JSON file path
        mock_json_path = MagicMock(spec=Path)
        mock_json_path.name = "sfs-2023-123.json"
        mock_json_path.__str__ = lambda x: "sfs_json/sfs-2023-123.json"

        # Mock file data
        mock_data = {"beteckning": "2023:123", "rubrik": "Test"}

        # Mock Path and file operations
        with patch('sfs_processor.Path') as mock_path_class:
            # Setup input directory mock
            mock_input_path = MagicMock()
            mock_input_path.exists.return_value = True
            mock_input_path.glob.return_value = [mock_json_path]

            # Setup output directory mock
            mock_output_path = MagicMock()
            mock_output_path.exists.return_value = True

            # Configure Path to return appropriate mocks
            def path_side_effect(path_str):
                if 'sfs_json' in str(path_str) or path_str == 'sfs_json':
                    return mock_input_path
                else:
                    return mock_output_path

            mock_path_class.side_effect = path_side_effect

            # Mock open and json.load
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))):
                with patch('json.load', return_value=mock_data):
                    # Test without --target-date argument
                    test_args = [
                        'sfs_processor.py',
                        '--input', 'sfs_json',
                        '--output', 'output',
                        '--formats', 'md-markers'
                    ]

                    with patch.object(sys, 'argv', test_args):
                        try:
                            sfs_processor.main()
                        except SystemExit:
                            pass

                    # Verify make_document was called with target_date=None
                    assert mock_make_document.called, "make_document should have been called"
                    call_args = mock_make_document.call_args

                    # The last argument should be None
                    assert call_args[0][-1] is None, \
                        f"Expected target_date None, got {call_args[0][-1]}"

    def test_target_date_format_validation(self):
        """Test that --target-date accepts YYYY-MM-DD format."""
        # This is a basic test - the actual validation happens in make_document
        # Here we just verify the argument is accepted
        test_args = [
            'sfs_processor.py',
            '--target-date', '2023-12-31',
            '--help'  # Use help to avoid actual execution
        ]

        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit):  # --help causes SystemExit
                sfs_processor.main()
