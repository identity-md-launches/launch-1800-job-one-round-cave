"""One-time delivery preservation pass for image-tool-generated pigment."""
import hashlib
import json
from pathlib import Path

from image_bytes import jpeg, png, read_png, resize


def main():
    folder = Path('artifacts/line-4')
    ancestor = (folder/'wall.png').read_bytes()
    generated = (folder/'wall-v12.png').read_bytes()
    assert hashlib.sha256(ancestor).hexdigest() == '53b0a3335c33b807890bd95ac044dabb202979ce1d48dce213e735b5f0da959d'
    assert hashlib.sha256(generated).hexdigest() == 'c8ea715075efee56171c20fd608876b6afbf2af9f1e3bac5d61da0379f52df1b'
    w, h, old = read_png(ancestor)
    gw, gh, draft = read_png(generated)
    assert (w, h, gw, gh) == (1254, 1254, 1254, 1254)
    final = bytearray(old)
    changed = 0
    for y in range(145, 215):
        for x in range(509, 679):
            i = (y*w+x)*3
            r, g, b = draft[i:i+3]
            original = old[i:i+3]
            if sum(original) < 80:
                continue  # Protect deep rock fissures.
            charcoal = r < 105 and g < 80 and b < 62 and r-g < 40 and sum(original)-sum((r,g,b)) > 30
            pebble = any((x-cx)**2+(y-cy)**2 < radius**2
                         for cx, cy, radius in ((534, 168, 16), (594, 189, 20), (652, 193, 16)))
            ochre = pebble and r > 1.4*g and r-g > 35
            chalk = (x-594)**2+(y-190)**2 < 7**2 and r > 145 and g > 110 and b > 75
            if charcoal:
                target = [v*.33 for v in original]
            elif ochre:
                target = [max(0, min(255, v*.25+p*.75)) for v, p in zip(original, (r, g, b))]
            elif chalk:
                target = [min(255, v*1.18+14) for v in original]
            else:
                continue
            final[i:i+3] = bytes(round(v*.15+t*.85) for v, t in zip(original, target))
            changed += final[i:i+3] != original
    assert 1000 < changed < 10000
    for i in range(0, len(old), 3):
        if old[i:i+3] != final[i:i+3]:
            y, x = divmod(i//3, w)
            assert 509 <= x < 679 and 145 <= y < 215 and sum(old[i:i+3]) >= 80
    wall = png(w, h, final)
    sha = hashlib.sha256(wall).hexdigest()
    preview = jpeg(512, 512, resize(w, h, final), 52)
    assert len(preview) < 100_000
    for name in ('wall.png', 'wall-v12.png'):
        (folder/name).write_bytes(wall)
    Path('dist/line-4/32.jpg').write_bytes(preview)
    review = {
        'wall': {'paths': ['artifacts/line-4/wall.png', 'artifacts/line-4/wall-v12.png'],
                 'width': w, 'height': h, 'format': 'PNG', 'mode': 'RGB', 'bytes': len(wall), 'sha256': sha},
        'preview': {'path': 'dist/line-4/32.jpg', 'width': 512, 'height': 512, 'format': 'JPEG',
                    'bytes': len(preview), 'sha256': hashlib.sha256(preview).hexdigest()},
        'ancestorSha256': hashlib.sha256(ancestor).hexdigest(),
        'generatedDraftSha256': hashlib.sha256(generated).hexdigest(),
        'imageTool': 'Built-in imagegen, generation 01a13d23-a53f-7dc3-b03b-07e7247fbd95',
        'prompt': 'Preserve the inherited square cave and every painting. Add a tiny worn charcoal cord threading three red-ochre beads, one with a chalk center, on vacant upper-center stone. No letters, numbers, hands or new figures.',
        'changedPixels': changed, 'unchangedPixels': w*h-changed,
        'additionBoundsExclusive': [509, 145, 679, 215],
        'preservation': 'All pixels outside the new vacant-stone pigment and all deep fissure pixels inside are identical to the hash-verified ancestor. Main Pepe, hands, older paintings, water and framing are untouched.',
        'visualReview': 'Pending final inspection.', 'unmetVisualRequirements': [],
        'limitations': ['Local observation is not independent visual certification.',
                       'The small worn motif is subtle at thumbnail scale.',
                       'The full generated draft changed surrounding texture; only its isolated new pigment was retained.'],
    }
    Path('line-4/wall-review-32.json').write_text(json.dumps(review, indent=2)+'\n')
    record = {
        'name': 'Each Bead in the Cord', 'image': 'https://api.imd.fun/artifacts/'+sha,
        'attributes': [
            {'trait_type': 'Cave', 'value': 'Water'}, {'trait_type': 'Wall', 'value': 'Line 4'},
            {'trait_type': 'Number', 'value': 32},
            {'trait_type': 'Left behind', 'value': 'offline EIP-712 byte reviewer'},
            {'trait_type': 'Meaning', 'value': 'Pepe checks each bead in a cord so no hidden byte can be exchanged.'},
            {'trait_type': 'One thing', 'value': 'offline EIP-712 typed-data digest checking'},
        ],
    }
    Path('dist/line-4/32.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
