import streamlit as st
import plotly.graph_objects as go
from math import floor
import copy

# -------------------- Default data --------------------
DEFAULT_PALLET = {'L': 42.0, 'W': 42.0, 'H': 90.0}
boxHeight_default = 9.0

DEFAULT_BOXES = {
    'AZ17': [40.0, 24.0, 9.0],
    'AZ13': [40.0, 16.0, 9.0],
    'AZ6': [40.0, 11.3, 9.0],
    'AZ16': [24.0, 20.0, 9.0],
    'AZ4': [24.0, 10.0, 9.0],
    'AZ3': [24.0, 8.0, 9.0],
    'AZ15': [22.9, 19.3, 9.0],
    'AZ11': [22.7, 13.0, 9.0],
    'AZ14': [22.375, 18.75, 9.0],
    'AZ10': [22.375, 12.75, 9.0],
    'AZ12': [20.0, 16.0, 9.0],
    'AZ8': [18.375, 11.6, 9.0],
    'AZ5': [18.375, 11.0, 9.0],
    'AZ7': [12.0, 11.375, 9.0],
    'AZ2': [12.0, 8.0, 9.0]
}

DEFAULT_ORDER = {
    'AZ17': 47,
    'AZ13': 12,
    'AZ6': 15,
    'AZ16': 72,
    'AZ4': 1,
    'AZ3': 64,
    'AZ15': 65,
    'AZ11': 24,
    'AZ14': 3,
    'AZ10': 12,
    'AZ12': 24,
    'AZ8': 24,
    'AZ5': 47,
    'AZ7': 24,
    'AZ2': 95
}

# -------------------- Packing logic --------------------
def build_info(boxes):
    info = {}
    for nm, dims in boxes.items():
        L, W, H = dims
        info[nm] = {'L': L, 'W': W, 'H': H, 'Area': L * W}
    return info


def try_place(free_rects, dims):
    for i, fr in enumerate(free_rects):
        fx, fy, fL, fW = fr
        L, W = dims
        if L <= fL and W <= fW:
            x, y = fx, fy
            new = free_rects.copy()
            new.pop(i)
            new.append([fx + L, fy, fL - L, W])
            new.append([fx, fy + W, fL, fW - W])
            return True, new, [x, y, L, W]
        if W <= fL and L <= fW:
            x, y = fx, fy
            new = free_rects.copy()
            new.pop(i)
            new.append([fx + W, fy, fL - W, L])
            new.append([fx, fy + L, fL, fW - L])
            return True, new, [x, y, W, L]
    return False, free_rects, [0, 0, 0, 0]


def pack_one_layer(pallet, boxes, order_left):
    placed_list = []
    free_rects = [[0.0, 0.0, pallet['L'], pallet['W']]]
    names = list(order_left.keys())
    valid = [n for n in names if order_left[n] > 0]
    if not valid:
        return placed_list, order_left

    valid.sort(key=lambda n: boxes[n]['Area'], reverse=True)
    for nm in valid:
        dims = [boxes[nm]['L'], boxes[nm]['W']]
        while order_left[nm] > 0:
            ok, new_free, pos = try_place(free_rects, dims)
            if not ok:
                break
            free_rects = new_free
            order_left[nm] -= 1
            placed_list.append({'name': nm, 'x': pos[0], 'y': pos[1], 'L': pos[2], 'W': pos[3]})

    rem_names = [n for n in names if order_left[n] > 0]
    if rem_names:
        rem_names.sort(key=lambda n: boxes[n]['Area'])
    r = 0
    while r < len(free_rects):
        fr = free_rects[r]
        filled = False
        for nm in rem_names:
            if order_left[nm] <= 0:
                continue
            dims = [boxes[nm]['L'], boxes[nm]['W']]
            ok, new_free, pos = try_place([fr], dims)
            if ok:
                order_left[nm] -= 1
                placed_list.append({'name': nm, 'x': pos[0], 'y': pos[1], 'L': pos[2], 'W': pos[3]})
                free_rects.pop(r)
                free_rects.extend(new_free)
                filled = True
                break
        if not filled:
            r += 1
    return placed_list, order_left


def pack_all_pallets(pallet, boxes, order, boxH):
    pallets = []
    pallet_layers = []
    order_left = copy.deepcopy(order)
    max_layers = int(floor(pallet['H'] / boxH))
    info = build_info(boxes)
    while sum(order_left.values()) > 0:
        layer_list = []
        for layer in range(max_layers):
            placed, order_left = pack_one_layer(pallet, info, order_left)
            if not placed:
                break
            layer_list.append(placed)
        if not layer_list:
            break
        pallet_layers.append(layer_list)
        pallets.append({})
    return pallets, pallet_layers


def plot_layer(pallet, layer_data, scale=10, title=None):
    L = pallet['L'] * scale
    W = pallet['W'] * scale
    fig = go.Figure()

    # Outer pallet rectangle
    fig.add_shape(type='rect', x0=0, y0=0, x1=L, y1=W, line=dict(width=2))

    colors = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b',
              '#e377c2','#7f7f7f','#bcbd22','#17becf']

    for i, d in enumerate(layer_data):
        x0 = d['x'] * scale
        y0 = d['y'] * scale
        x1 = x0 + d['L'] * scale
        y1 = y0 + d['W'] * scale
        color = colors[i % len(colors)]

        # Draw the box
        fig.add_shape(
            type='rect',
            x0=x0, y0=y0, x1=x1, y1=y1,
            line=dict(color='black', width=1),
            fillcolor=color, opacity=0.7
        )

        # Add permanent label on top of box
        fig.add_annotation(
            x=(x0 + x1)/2, y=(y0 + y1)/2,
            text=d['name'],
            showarrow=False,
            font=dict(color='black', size=14, family='Arial Black'),
            xanchor='center', yanchor='middle'
        )

    fig.update_xaxes(showticklabels=False, range=[0, L])
    fig.update_yaxes(showticklabels=False, range=[0, W], scaleanchor='x', scaleratio=1)
    fig.update_layout(
        width=600, height=600 * (pallet['W']/pallet['L']),
        margin=dict(l=10,r=10,t=30,b=10),
    )
    if title:
        fig.update_layout(title=title)
    return fig


# -------------------- Streamlit UI --------------------
st.set_page_config(page_title='Pallet Packing Dashboard', layout='wide')
st.title('Pallet Packing Dashboard (Streamlit)')

with st.sidebar:
    st.header('Inputs')
    pallet_L = st.number_input('Pallet length (in)', value=float(DEFAULT_PALLET['L']))
    pallet_W = st.number_input('Pallet width (in)', value=float(DEFAULT_PALLET['W']))
    pallet_H = st.number_input('Pallet height (in)', value=float(DEFAULT_PALLET['H']))
    boxH = st.number_input('Box height (in)', value=float(boxHeight_default))
    scale = st.number_input('Scale factor (visual)', value=8)
    st.markdown('---')
    orders_text = st.text_area('Order (CSV: name,qty per line)',
                               value='\n'.join([f'{k},{v}' for k,v in DEFAULT_ORDER.items()]),
                               height=200)
    use_defaults = st.checkbox('Use default boxes definitions', value=True)

order = {}
for line in orders_text.splitlines():
    if not line.strip():
        continue
    parts = [p.strip() for p in line.split(',') if p.strip()]
    if len(parts) >= 2:
        order[parts[0]] = int(float(parts[1]))

boxes = DEFAULT_BOXES if use_defaults else DEFAULT_BOXES.copy()
pallet = {'L': pallet_L, 'W': pallet_W, 'H': pallet_H}

pallets, layerDetails = pack_all_pallets(pallet, boxes, order, boxH)
st.success(f'Total pallets used: {len(pallets)}')

# Display all pallets and layers (10 layers per row)
for p_idx, layers in enumerate(layerDetails):
    st.subheader(f'Pallet {p_idx+1} — {len(layers)} layer(s)')
    nCols = 2
    cols = st.columns(nCols)
    for l_idx, layer in enumerate(layers):
        fig = plot_layer(pallet, layer, scale=scale, title=f'Layer {l_idx+1}')
        col_idx = l_idx % nCols
        st.plotly_chart(fig, use_container_width=True, key=f'p{p_idx}_l{l_idx}')
