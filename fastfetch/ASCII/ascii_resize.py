#!/usr/bin/env python3
"""
ascii_resize.py — Reduz a resolução de ASCII/ANSI art sem perder detalhes.

Uso:
    python3 ascii_resize.py input.txt  output.txt  --width 60
    python3 ascii_resize.py input.ansi output.ansi --width 60
    python3 ascii_resize.py input.ansi output.ansi --scale 0.5
    python3 ascii_resize.py input.ansi output.ansi --width 60 --height 30
    cat input.ansi | python3 ascii_resize.py - - --width 60

Estratégia para .txt / ASCII puro:
    Para cada bloco de N×M caracteres, escolhe o representante pela
    mediana de densidade visual (Braille: conta pontos acesos no Unicode).

Estratégia para .ansi / texto com escape codes ANSI:
    Cada célula é um par (char, escape_code). O bloco vencedor é o char
    de maior densidade; ele carrega consigo o escape code da célula
    original, preservando as cores exatamente onde há mais detalhe visual.
    Sequências de reset/formatação são reemitidas corretamente na saída.
"""

import re
import sys
import argparse
import unicodedata
from typing import List, Tuple, Optional


# ---------------------------------------------------------------------------
# Densidade visual
# ---------------------------------------------------------------------------

_DENSITY_CACHE: dict = {}

def _char_density(ch: str) -> float:
    """Retorna 0..1 indicando a densidade visual do caractere."""
    if ch in _DENSITY_CACHE:
        return _DENSITY_CACHE[ch]

    cp = ord(ch)
    if 0x2800 <= cp <= 0x28FF:
        density = bin(cp - 0x2800).count('1') / 8.0
    elif ch in (' ', '\u00a0', '\t'):
        density = 0.0
    else:
        w = unicodedata.east_asian_width(ch)
        density = 0.7 if w in ('W', 'F') else 0.5

    _DENSITY_CACHE[ch] = density
    return density


# ---------------------------------------------------------------------------
# Parser de ANSI escape codes
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r'\x1b(?:\[[0-9;]*[a-zA-Z]|\(B|[=><]|[^[])')

def _strip_ansi(text: str) -> str:
    """Remove todos os escape codes ANSI, retornando só os caracteres visíveis."""
    return _ANSI_RE.sub('', text)


# Célula ANSI: (char_visível, escape_code_que_precede_este_char)
def _parse_ansi_line(line: str) -> List[Tuple[str, str]]:
    """
    Parseia uma linha com ANSI codes e retorna lista de (char, ansi_prefix).
    """
    cells = []
    pending_escape = ''
    i = 0
    while i < len(line):
        m = _ANSI_RE.match(line, i)
        if m:
            pending_escape += m.group(0)
            i = m.end()
        else:
            ch = line[i]
            cells.append((ch, pending_escape))
            pending_escape = ''
            i += 1
    return cells


def _build_ansi_line(cells: List[Tuple[str, str]]) -> str:
    """
    Reconstrói uma linha a partir de células (char, ansi_prefix),
    comprimindo escapes redundantes consecutivos.
    """
    parts = []
    last_escape = None
    for ch, esc in cells:
        if esc != last_escape:
            parts.append(esc)
            last_escape = esc
        parts.append(ch)
    parts.append('\x1b[0m')  # reset no fim para não vazar cor
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Lógica de bloco
# ---------------------------------------------------------------------------

def _block_winner_plain(chars: List[str]) -> str:
    """Vencedor de bloco para ASCII puro (sem ANSI)."""
    if not chars:
        return ' '
    non_space = [c for c in chars if c.strip()]
    pool = non_space if non_space else chars
    pool_sorted = sorted(pool, key=_char_density)
    return pool_sorted[len(pool_sorted) // 2]


def _block_winner_ansi(cells: List[Tuple[str, str]]) -> Tuple[str, str]:
    """
    Vencedor de bloco para ANSI: retorna a célula com o char de maior
    densidade (mediana), preservando o escape code original dessa célula.
    """
    if not cells:
        return (' ', '')
    non_space = [(ch, esc) for ch, esc in cells if ch.strip()]
    pool = non_space if non_space else cells
    pool_sorted = sorted(pool, key=lambda c: _char_density(c[0]))
    return pool_sorted[len(pool_sorted) // 2]


# ---------------------------------------------------------------------------
# Carregamento
# ---------------------------------------------------------------------------

def _read_raw(path: str) -> bytes:
    if path == '-':
        return sys.stdin.buffer.read()
    with open(path, 'rb') as f:
        return f.read()


def load_file(path: str) -> Tuple[List[str], bool]:
    """
    Retorna (linhas, is_ansi).
    Detecta automaticamente se o arquivo contém ANSI codes.
    """
    raw = _read_raw(path)
    text = raw.decode('utf-8', errors='replace')
    lines = text.splitlines()
    is_ansi = b'\x1b[' in raw or b'\x1b(' in raw
    return lines, is_ansi


# ---------------------------------------------------------------------------
# Resize
# ---------------------------------------------------------------------------

def _compute_targets(orig_w, orig_h, target_width, target_height, scale):
    if scale is not None:
        return max(1, int(orig_w * scale)), max(1, int(orig_h * scale))
    return (target_width or orig_w), (target_height or orig_h)


def _block_range(idx, total_in, total_out):
    """Retorna (start, end) do bloco idx no grid original."""
    b = total_in / total_out
    start = int(idx * b)
    end = min(max(start + 1, int((idx + 1) * b)), total_in)
    return start, end


def resize_plain(lines, target_width=None, target_height=None, scale=None):
    """Resize para ASCII puro."""
    if not lines:
        return []

    orig_h = len(lines)
    orig_w = max(len(l) for l in lines)
    lines = [l.ljust(orig_w) for l in lines]

    tw, th = _compute_targets(orig_w, orig_h, target_width, target_height, scale)

    result = []
    for row in range(th):
        r0, r1 = _block_range(row, orig_h, th)
        out_row = []
        for col in range(tw):
            c0, c1 = _block_range(col, orig_w, tw)
            block = [
                lines[r][c]
                for r in range(r0, r1)
                for c in range(c0, c1)
                if c < len(lines[r])
            ]
            out_row.append(_block_winner_plain(block))
        result.append(''.join(out_row))
    return result


def resize_ansi(lines, target_width=None, target_height=None, scale=None):
    """
    Resize para ANSI art.
    Parseia cada linha em células (char, ansi_prefix), faz downsampling
    preservando os escape codes das células vencedoras e reconstrói as linhas.
    """
    if not lines:
        return []

    parsed = [_parse_ansi_line(l) for l in lines]

    orig_h = len(parsed)
    orig_w = max((len(row) for row in parsed), default=0)

    # Pad com células vazias
    parsed = [row + [(' ', '')] * (orig_w - len(row)) for row in parsed]

    tw, th = _compute_targets(orig_w, orig_h, target_width, target_height, scale)

    result = []
    for row in range(th):
        r0, r1 = _block_range(row, orig_h, th)
        out_row = []
        for col in range(tw):
            c0, c1 = _block_range(col, orig_w, tw)
            block = [
                parsed[r][c]
                for r in range(r0, r1)
                for c in range(c0, c1)
                if c < len(parsed[r])
            ]
            out_row.append(_block_winner_ansi(block))
        result.append(_build_ansi_line(out_row))

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Reduz resolução de ASCII/ANSI art preservando detalhes.'
    )
    parser.add_argument('input',  help='Arquivo de entrada (use - para stdin)')
    parser.add_argument('output', help='Arquivo de saída  (use - para stdout)')
    parser.add_argument('--width',    type=int,   help='Largura alvo em caracteres')
    parser.add_argument('--height',   type=int,   help='Altura alvo em linhas')
    parser.add_argument('--scale',    type=float, help='Fator de escala (ex: 0.5 = metade)')
    parser.add_argument('--ansi',     action='store_true', help='Força modo ANSI')
    parser.add_argument('--no-ansi',  action='store_true', help='Força modo texto puro (strips ANSI codes)')
    args = parser.parse_args()

    if args.scale is None and args.width is None and args.height is None:
        parser.error('Informe --width, --height ou --scale.')

    lines, detected_ansi = load_file(args.input)

    if args.no_ansi:
        use_ansi = False
        lines = [_strip_ansi(l) for l in lines]
    elif args.ansi:
        use_ansi = True
    else:
        use_ansi = detected_ansi

    mode_label = 'ANSI' if use_ansi else 'texto puro'

    if use_ansi:
        resized = resize_ansi(lines, target_width=args.width, target_height=args.height, scale=args.scale)
    else:
        resized = resize_plain(lines, target_width=args.width, target_height=args.height, scale=args.scale)

    output_text = '\n'.join(resized) + '\n'

    if args.output == '-':
        sys.stdout.buffer.write(output_text.encode('utf-8'))
    else:
        with open(args.output, 'wb') as f:
            f.write(output_text.encode('utf-8'))

    if args.output != '-':
        orig_w  = max(len(_strip_ansi(l)) for l in lines)  if use_ansi else max(len(l) for l in lines)
        new_w   = max(len(_strip_ansi(l)) for l in resized) if use_ansi else max(len(l) for l in resized)
        print(f'[{mode_label}] {len(lines)}×{orig_w} → {len(resized)}×{new_w} caracteres')


if __name__ == '__main__':
    main()