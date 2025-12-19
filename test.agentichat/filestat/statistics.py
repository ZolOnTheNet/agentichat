#!/usr/bin/env python3

import os
def count_characters_and_words(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        num_chars = len(content)
        words = content.split()
        num_words = len(words)
        return num_chars, num_words

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage: python statistics.py <file_path>')
    else:
        file_path = sys.argv[1]
        chars, words = count_characters_and_words(file_path)
        print(f'Number of characters: {chars}')
        print(f'Number of words: {words}')