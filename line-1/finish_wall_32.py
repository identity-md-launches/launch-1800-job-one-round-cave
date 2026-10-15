"""Add the image-generated comparison mark to record 31's exact wall bytes."""
import hashlib
import json
from pathlib import Path
from image_bytes import read_png, png, resize, jpeg

BASE = Path('artifacts/line-1/wall.png')
OUT = Path('artifacts/line-1/wall-v12.png')
ANCESTOR = '3767f4c32073fc2fab037ae1ea75fba9b040e518b4e70eeac56742654e359b0f'


def main():
    original = BASE.read_bytes()
    assert hashlib.sha256(original).hexdigest() == ANCESTOR
    w, h, old = read_png(original)
    draft = OUT.read_bytes()
    gw, gh, generated = read_png(draft)
    assert (w, h) == (gw, gh) == (1254, 1254)
    final = bytearray(old)
    changed = 0
    bounds = [w, h, 0, 0]
    # The ancestor has bare rock here. Feather only this small oval; all earlier
    # pigment, Pepe, cracks elsewhere and the cave framing remain byte-exact.
    for y in range(420, 539):
        for x in range(996, 1149):
            radial = ((x - 1072) / 76) ** 2 + ((y - 479) / 59) ** 2
            if radial >= 1:
                continue
            alpha = 0.88 if radial <= 0.73 else 0.88 * (1-radial) / 0.27
            i = (y*w+x)*3
            for channel in range(3):
                final[i+channel] = round((1-alpha)*old[i+channel] +
                                         alpha*generated[i+channel])
            if final[i:i+3] != old[i:i+3]:
                changed += 1
                bounds = [min(bounds[0], x), min(bounds[1], y),
                          max(bounds[2], x), max(bounds[3], y)]
    assert 5000 < changed < 20000
    encoded = png(w, h, final)
    BASE.write_bytes(encoded)
    OUT.write_bytes(encoded)
    thumb = jpeg(512, 512, resize(w, h, final), 52)
    assert len(thumb) < 100000
    Path('dist/line-1/32.jpg').write_bytes(thumb)
    wall_hash = hashlib.sha256(encoded).hexdigest()
    record = {
        'name': 'The Compared Pebbles',
        'image': 'https://api.imd.fun/artifacts/' + wall_hash,
        'attributes': [
            {'trait_type': 'Cave', 'value': 'Water'},
            {'trait_type': 'Wall', 'value': 'Line 1'},
            {'trait_type': 'Number', 'value': 32},
            {'trait_type': 'Left behind', 'value': 'Generic snapshot diff'},
            {'trait_type': 'Meaning', 'value': 'Two ochre pebbles let Pepe compare saved answers while keeping each observation distinct.'},
            {'trait_type': 'One thing', 'value': 'portable live Ethereum JSON-RPC snapshots'},
        ],
    }
    Path('dist/line-1/32.json').write_text(json.dumps(record, indent=2) + '\n')
    review = {
        'record': 32,
        'ancestor_sha256': ANCESTOR,
        'output_sha256': wall_hash,
        'wall': {'paths': [str(BASE), str(OUT)], 'format': 'PNG',
                 'width': w, 'height': h, 'mode': 'RGB'},
        'thumbnail': {'path': 'dist/line-1/32.jpg', 'format': 'JPEG',
                      'width': 512, 'height': 512, 'bytes': len(thumb)},
        'generation': {'tool': 'image_gen.imagegen',
                       'draft_sha256': hashlib.sha256(draft).hexdigest(),
                       'draft_retained': False},
        'preservation': 'Every pixel outside the small new feathered oval is exactly ancestral.',
        'changed_pixels': changed,
        'unchanged_pixels': w*h-changed,
        'changed_bounds_inclusive': bounds,
        'visual_review': 'Pending final inspection',
        'unmet_visual_requirements': [],
    }
    Path('line-1/wall-review-32.json').write_text(json.dumps(review, indent=2) + '\n')
    print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
