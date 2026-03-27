"""
Text cleaner module for the RAG Book Ingestion Pipeline.
Handles cleaning and normalization of extracted text.
"""

import re
from typing import List, Dict
from .logger import ingestion_logger


class TextCleaner:
    """
    Cleans and normalizes extracted text to prepare it for chunking and embedding.
    """

    def __init__(self):
        # Common patterns to remove or replace
        self.patterns = [
            # Remove multiple consecutive newlines (more than 2)
            (r'\n{3,}', '\n\n'),
            # Remove excessive whitespace
            (r'[ \t]+', ' '),
            # Remove special characters that might interfere with processing
            (r'[^\x00-\x7F]+', ''),  # Remove non-ASCII characters if needed
        ]

    def clean_text(self, text: str) -> str:
        """
        Clean a single text string.

        Args:
            text: The text to clean

        Returns:
            str: Cleaned text
        """
        if not text:
            return text

        original_length = len(text)

        # Apply cleaning patterns
        for pattern, replacement in self.patterns:
            text = re.sub(pattern, replacement, text)

        # Additional cleaning steps
        text = self._remove_excessive_whitespace(text)
        text = self._normalize_line_endings(text)
        text = text.strip()

        # Log if significant changes occurred
        if len(text) != original_length:
            change_percent = abs(len(text) - original_length) / original_length * 100
            if change_percent > 10:  # If more than 10% change
                ingestion_logger.info(f"Text cleaning resulted in {change_percent:.1f}% size change")

        return text

    def _remove_excessive_whitespace(self, text: str) -> str:
        """
        Remove excessive whitespace while preserving necessary formatting.

        Args:
            text: The text to process

        Returns:
            str: Text with normalized whitespace
        """
        # Replace multiple spaces with single space, but preserve newlines
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove leading/trailing whitespace from each line
            line = line.strip()
            if line:  # Only add non-empty lines
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _normalize_line_endings(self, text: str) -> str:
        """
        Normalize different line ending styles to \n.

        Args:
            text: The text to process

        Returns:
            str: Text with normalized line endings
        """
        return text.replace('\r\n', '\n').replace('\r', '\n')

    def clean_batch(self, texts: List[str]) -> List[str]:
        """
        Clean a batch of texts.

        Args:
            texts: List of texts to clean

        Returns:
            List[str]: List of cleaned texts
        """
        cleaned_texts = []
        for text in texts:
            cleaned_texts.append(self.clean_text(text))
        return cleaned_texts

    def remove_code_blocks(self, text: str) -> str:
        """
        Remove code blocks from text while preserving the rest.

        Args:
            text: The text to process

        Returns:
            str: Text with code blocks removed
        """
        # Remove code blocks in triple backticks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # Remove inline code
        text = re.sub(r'`(.*?)`', r'\1', text)  # Just remove backticks, keep content
        return text

    def preserve_code_blocks(self, text: str) -> tuple:
        """
        Extract code blocks from text and return both the cleaned text and code blocks.

        Args:
            text: The text to process

        Returns:
            tuple: (cleaned_text, list_of_code_blocks)
        """
        code_blocks = []
        # Find and extract code blocks
        code_pattern = r'```.*?```'
        code_blocks = re.findall(code_pattern, text, flags=re.DOTALL)

        # Remove code blocks from text
        cleaned_text = re.sub(code_pattern, '<CODE_BLOCK>', text, flags=re.DOTALL)

        return cleaned_text, code_blocks

    def restore_code_blocks(self, text: str, code_blocks: List[str]) -> str:
        """
        Restore code blocks back into text.

        Args:
            text: The text with placeholders
            code_blocks: List of code blocks to restore

        Returns:
            str: Text with code blocks restored
        """
        for code_block in code_blocks:
            text = text.replace('<CODE_BLOCK>', code_block, 1)
        return text


def clean_text(text: str) -> str:
    """
    Convenience function to clean text.

    Args:
        text: The text to clean

    Returns:
        str: Cleaned text
    """
    cleaner = TextCleaner()
    return cleaner.clean_text(text)


def clean_batch(texts: List[str]) -> List[str]:
    """
    Convenience function to clean a batch of texts.

    Args:
        texts: List of texts to clean

    Returns:
        List[str]: List of cleaned texts
    """
    cleaner = TextCleaner()
    return cleaner.clean_batch(texts)


if __name__ == "__main__":
    # Test the text cleaner
    print("Testing text cleaner...")

    test_text = """
    This is a   sample text with excessive     whitespace.


    It also has multiple empty lines.

    And some `inline code` here.
    ```
    def sample_code():
        pass
    ```
    More text here.
    """

    cleaner = TextCleaner()
    cleaned = cleaner.clean_text(test_text)

    print("Original text length:", len(test_text))
    print("Cleaned text length:", len(cleaned))
    print("\nCleaned text:")
    print(cleaned)