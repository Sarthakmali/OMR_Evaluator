import cv2
import numpy as np
import json

SECTION_MAP = {
    "Python": "Python",
    "EDA": "EDA",
    "SQL": "SQL",
    "Power BI": "Power BI",
    "Statistics": "Statistics"
}
SECTION_RANGES = {
    "Python": (1, 20),
    "EDA": (21, 40),
    "SQL": (41, 60),
    "Power BI": (61, 80),
    "Statistics": (81, 100)
}
OPTION_LETTERS = ['a', 'b', 'c', 'd']
NUM_QUESTIONS = 100
NUM_COLS = 5
NUM_ROWS_PER_COL = 20
NUM_OPTS = 4
FILL_THRESH = 0.27

def create_standard_grid_crop_with_aspect_ratio(img, target_size=(800, 1000), padding=80):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 13, 8)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bubbles = []
    for c in contours:
        area = cv2.contourArea(c)
        x, y, w, h = cv2.boundingRect(c)
        aspect_ratio = float(w) / h
        if 100 < area < 3000 and 0.3 < aspect_ratio < 3.0 and w > 5 and h > 5:
            bubbles.append((x, y, w, h))
    if len(bubbles) < 50:
        print(f"Only found {len(bubbles)} bubbles")
        return None
    xs = sorted([x for x, y, w, h in bubbles])
    ys = sorted([y for x, y, w, h in bubbles])
    x_rights = sorted([x+w for x, y, w, h in bubbles])
    y_bottoms = sorted([y+h for x, y, w, h in bubbles])
    left = xs[int(len(xs) * 0.05)]
    right = x_rights[int(len(x_rights) * 0.95)]
    top = ys[int(len(ys) * 0.05)]
    bottom = y_bottoms[int(len(y_bottoms) * 0.95)]
    crop_left = max(0, left - padding)
    crop_right = min(img.shape[1], right + padding)
    crop_top = max(0, top - padding)
    crop_bottom = min(img.shape[0], bottom + padding)
    grid_crop = img[crop_top:crop_bottom, crop_left:crop_right]
    crop_height, crop_width = grid_crop.shape[:2]
    target_width, target_height = target_size
    scale_x = target_width / crop_width
    scale_y = target_height / crop_height
    scale = min(scale_x, scale_y)
    new_width = int(crop_width * scale)
    new_height = int(crop_height * scale)
    resized_grid = cv2.resize(grid_crop, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    final_image = np.ones((target_height, target_width, 3), dtype=np.uint8) * 255
    start_x = (target_width - new_width) // 2
    start_y = (target_height - new_height) // 2
    final_image[start_y:start_y+new_height, start_x:start_x+new_width] = resized_grid
    return final_image

def cluster_bubbles_by_row(contours, min_area=120, max_area=400, min_aspect=0.7, max_aspect=1.4, min_w=10, min_h=10, min_circularity=0.65):
    bubbles = []
    for c in contours:
        area = cv2.contourArea(c)
        x, y, w, h = cv2.boundingRect(c)
        aspect_ratio = float(w) / h
        perimeter = cv2.arcLength(c, True)
        circularity = (4 * np.pi * area / (perimeter * perimeter)) if perimeter > 0 else 0
        if min_area < area < max_area and min_aspect < aspect_ratio < max_aspect and w > min_w and h > min_h and circularity > min_circularity:
            bubbles.append((x, y, w, h, c))
    bubbles.sort(key=lambda b: b[1])  # sort top → bottom
    if not bubbles:
        return []
    rows = []
    current_row = []
    row_threshold = 20
    last_y = None
    for b in bubbles:
        if last_y is None or abs(b[1]-last_y) < row_threshold:
            current_row.append(b)
        else:
            rows.append(current_row)
            current_row = [b]
        last_y = b[1]
    if current_row:
        rows.append(current_row)
    return rows

def omr_detect_and_score(image_path, answerkey_path):
    img = cv2.imread(image_path)
    if img is None:
        raise Exception("Image read failed!")
    grid_img = create_standard_grid_crop_with_aspect_ratio(img, target_size=(800, 1000))
    if grid_img is None:
        raise Exception("Could not standardize OMR grid area")
    gray = cv2.cvtColor(grid_img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 13, 8)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rows = cluster_bubbles_by_row(
        contours,
        min_area=50,
        max_area=650,
        min_aspect=0.65,
        max_aspect=1.45,
        min_w=13,
        min_h=12,
        min_circularity=0.7
    )
    detected_bubbles = []
    for row in rows:
        for b in row:
            detected_bubbles.append(b)
    detected_bubbles.sort(key=lambda b: b[0])
    bubbles_per_col = len(detected_bubbles) // NUM_COLS
    questions = [[] for _ in range(NUM_QUESTIONS)]
    for col in range(NUM_COLS):
        col_bubbles = detected_bubbles[col * bubbles_per_col : (col + 1) * bubbles_per_col]
        col_bubbles.sort(key=lambda b: b[1])
        for row in range(NUM_ROWS_PER_COL):
            group = col_bubbles[row * NUM_OPTS : (row + 1) * NUM_OPTS]
            group = sorted(group, key=lambda b: b[0])
            ans = []
            for b_idx, (x, y, w, h, c) in enumerate(group):
                roi = gray[int(y+0.2*h):int(y+0.8*h), int(x+0.2*w):int(x+0.8*w)]
                if roi.size == 0:
                    continue
                black_ratio = np.mean(roi < 100)
                mean_val = np.mean(roi)
                if black_ratio > FILL_THRESH or mean_val < 140:
                    ans.append(OPTION_LETTERS[b_idx])
            qnum = col * NUM_ROWS_PER_COL + row
            questions[qnum] = ans
    
    # Build section-wise dict
    detected_sectionwise = {}
    for section, (startq, endq) in SECTION_RANGES.items():
        detected_sectionwise[section] = {}
        for q in range(startq, endq+1):
            idx = q - 1
            val = questions[idx]
            ans = ",".join(val) if len(val) > 1 else (val[0] if val else "")
            detected_sectionwise[section][f"Q{q}"] = ans.lower()
    
    with open(answerkey_path, "r") as f:
        answer_key = json.load(f)
    # The answer_key is also sectionwise
    
    def norm(ans): return "".join(sorted(ans.replace(",", "").replace(" ", "").lower()))
    section_scores = {}
    total = 0
    for section in SECTION_MAP:
        subs = detected_sectionwise[section]
        keysubs = answer_key.get(section, {})
        count = 0
        for q in subs:
            stu_ans = norm(subs.get(q,""))
            key_ans = norm(keysubs.get(q[1:] if section=="Python" else q,"")) # keys might be Q1 or 1; patch as you need
            if stu_ans and key_ans and stu_ans == key_ans:
                count += 1
        section_scores[section] = count
        total += count
    section_scores["Total"] = total

    return detected_sectionwise, section_scores
