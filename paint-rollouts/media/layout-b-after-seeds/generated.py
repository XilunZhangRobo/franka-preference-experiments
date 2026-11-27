pickup_x = [-255, -153, -51, 51, 153, 255]
shelf_x = [-255, -153, -51, 51, 153, 255]
pickup_order = [0, 2, 4, 5, 1, 3]
for slot in range(6):
    move(pickup_x[pickup_order[slot]], -174, shelf_x[slot], 50, 40, 0, 19)
