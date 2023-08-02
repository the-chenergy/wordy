import util

import prompt_toolkit, prompt_toolkit.completion, prompt_toolkit.document

import argparse, collections, os, pathlib, random, re, sys, typing

import readline  # enhances input interaction (enables arrow keys, for example)


def main() -> None:
    BLACK_CLUE = '_'
    YELLOW_CLUE = '^'
    GREEN_CLUE = '#'

    REVEAL_COMMAND = '!'
    HINT_COMMAND = '?'
    CLEAR_COMMAND = '/'

    def parse_cli_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        parser.description = (
            'Play Wordle offline\n'
            '\n'
            'Legend:\n'
            f'\t{BLACK_CLUE} => black\n'
            f'\t{YELLOW_CLUE} => yellow\n'
            f'\t{GREEN_CLUE} => green\n'
            '\n'
            'Special commands (enter at any point to activate):\n'
            f'\t{REVEAL_COMMAND} => reveal the target word\n'
            f'\t{HINT_COMMAND} => receive a hint (a possible target word)\n'
            f'\t{CLEAR_COMMAND} => clear invalid guesses')
        parser.formatter_class = argparse.RawTextHelpFormatter

        parser.add_argument(
            '-t',
            '--target',
            help=
            'set the target word (case insensitive; default: randomly chosen from allowed target words)'
        )
        DEFAULT_GUESSES_LIMIT = 6
        parser.add_argument(
            '-l',
            '--limit',
            type=int,
            default=DEFAULT_GUESSES_LIMIT,
            help=
            f'set maximum number of guesses, or 0 for no limit (default: {DEFAULT_GUESSES_LIMIT})'
        )
        CURRENT_DIR_PATH = os.path.dirname(__file__)
        DEFAULT_ALLOWED_TARGETS_FILE = f'{CURRENT_DIR_PATH}/allowed_targets.txt'
        parser.add_argument(
            '-f',
            '--targets',
            type=pathlib.Path,
            default=DEFAULT_ALLOWED_TARGETS_FILE,
            help=
            f'set file with list of allowed target words (default: "{DEFAULT_ALLOWED_TARGETS_FILE}")'
        )
        parser.add_argument(
            '-T',
            '--top',
            type=int,
            help=
            'only choose target from the top X words in the list (default: choose from whole list)'
        )
        DEFAULT_ALLOWED_GUESSES_FILE = f'{CURRENT_DIR_PATH}/./allowed_guesses.txt'
        parser.add_argument(
            '-g',
            '--guesses',
            type=pathlib.Path,
            default=DEFAULT_ALLOWED_GUESSES_FILE,
            help=
            f'set file with list of allowed guesses (default: "{DEFAULT_ALLOWED_GUESSES_FILE}")'
        )
        parser.add_argument(
            '-H',
            '--hard',
            type=bool,
            action=argparse.BooleanOptionalAction,
            help=
            f'hard mode: future guesses must obey all revealed clues (including black "{BLACK_CLUE}" clues, which is in addition to NYTimes\' rules for hard mode)'
        )
        parser.add_argument(
            '-a',
            '--any',
            type=bool,
            action=argparse.BooleanOptionalAction,
            help='allow guesses to be any string with same length as target')
        parser.add_argument(
            '-c',
            '--completion',
            type=bool,
            action=argparse.BooleanOptionalAction,
            help='enable tab completion, activated by the tab key')

        return parser.parse_args(sys.argv[1:])

    cli_args = parse_cli_args()

    allowed_targets = util.parse_word_list(cli_args.targets,
                                           limit=cli_args.top)
    allowed_guesses = util.parse_word_list(cli_args.guesses)
    assert len(allowed_targets[0]) == len(allowed_guesses[0])

    if cli_args.target is not None: target = str.lower(cli_args.target)
    else: target = random.choice(allowed_targets)

    guesses_limit = int(cli_args.limit)
    if guesses_limit <= 0: guesses_limit = 1 << 31

    guesses_used = 0
    prev_guesses: list[str] = []
    prev_clues: list[list[str]] = []

    def possible(guess: str, check_black_letters: bool = True) -> bool:
        for prev_guess, prev_clue in zip(prev_guesses, prev_clues):
            prev_counts = collections.Counter()
            bounded = set()
            for i in range(len(target)):
                if prev_clue[i] != BLACK_CLUE: prev_counts[prev_guess[i]] += 1
            for i in range(len(target)):
                if prev_clue[i] == BLACK_CLUE:
                    if guess[i] == prev_guess[i]: return False
                    bounded.add(prev_guess[i])
            guess_counts = collections.Counter(guess)
            if check_black_letters:
                for letter in guess_counts:
                    if (letter in bounded
                            and guess_counts[letter] > prev_counts[letter]):
                        return False
            for i in range(len(target)):
                if prev_clue[i] == GREEN_CLUE and guess[i] != prev_guess[i]:
                    return False
                if prev_clue[i] == YELLOW_CLUE and guess[i] == prev_guess[i]:
                    return False
            for letter in prev_counts:
                if guess_counts[letter] < prev_counts[letter]: return False
        return True

    def gen_hints() -> typing.Iterator[str]:
        shuffled_targets = allowed_targets.copy()
        random.shuffle(shuffled_targets)
        for word in shuffled_targets:
            if possible(word): yield word

    hints = gen_hints()

    class WordCompleter(prompt_toolkit.completion.WordCompleter):
        def __init__(self, words: list[str]) -> None:
            super().__init__(words)
            self.words = words

        def get_completions(
            self, document: prompt_toolkit.document.Document,
            complete_event: prompt_toolkit.completion.CompleteEvent
        ) -> typing.Iterable[prompt_toolkit.completion.Completion]:
            entered_text = document.current_line.replace('_', '.').lower()
            for word in self.words:
                if re.match(entered_text, word) is not None:
                    yield prompt_toolkit.completion.Completion(
                        word, -len(entered_text))

    tab_completer = WordCompleter(sorted(allowed_targets))

    while True:
        prompt = f'{guesses_used + 1}. '
        guess = prompt_toolkit.prompt(
            prompt,
            completer=tab_completer if cli_args.completion else None,
            complete_while_typing=False,
        )
        guess = guess.strip().lower()
        message_indent = ' ' * len(prompt)

        if guess == REVEAL_COMMAND:
            print('\nAnswer:', target)
            break

        if guess == HINT_COMMAND:
            try:
                hint = next(hints)
                print(message_indent + f'(hint: {hint})\n')
            except StopIteration:
                print(message_indent + '(can\'t find a hint)\n')
                hints = gen_hints()
            continue

        if guess == CLEAR_COMMAND:
            os.system('cls || clear')
            for i in range(len(prev_guesses)):
                prev_prompt = f'{i + 1}. '
                print(prev_prompt + prev_guesses[i])
                print(' ' * len(prev_prompt) + ''.join(prev_clues[i]) + '\n')
            continue

        if guess == target:
            print(message_indent + GREEN_CLUE * len(target) + '\n')
            WIN_TEXTS = [
                'Genius!', 'Magnificent!', 'Impressive!', 'Splendid!',
                'Great!', 'Phew!'
            ]
            print(WIN_TEXTS[guesses_used])
            break

        if len(guess) != len(target):
            print(message_indent + f'(wrong length; target: {len(target)})\n')
            continue

        if not cli_args.any and guess not in allowed_guesses:
            print(message_indent + '(not a word)\n')
            continue

        if cli_args.hard and not possible(guess):
            print(message_indent + '(violates clues)\n')
            continue

        clue = [BLACK_CLUE] * len(target)
        target_counts = collections.Counter(target)
        for i in range(len(target)):
            if guess[i] == target[i]:
                clue[i] = GREEN_CLUE
                target_counts[guess[i]] -= 1
        for i in range(len(target)):
            if guess[i] != target[i] and target_counts[guess[i]] > 0:
                clue[i] = YELLOW_CLUE
                target_counts[guess[i]] -= 1
        print(message_indent + ''.join(clue) + '\n')

        guesses_used += 1
        if guesses_used == guesses_limit:
            print('Answer:', target)
            break

        prev_guesses.append(guess)
        prev_clues.append(clue)
        hints = gen_hints()


if __name__ == '__main__':
    main()
