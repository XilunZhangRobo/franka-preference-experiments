pickup_x = [-255, -153, -51, 51, 153, 255]
shelf_x = [-255, -153, -51, 51, 153, 255]
order = [1, 3, 4, 5, 0, 2]
for slot in range(6):
    move(pickup_x[order[slot]], -174, shelf_x[slot], 50, 40, 0, 19)
