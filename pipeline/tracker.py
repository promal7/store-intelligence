import math

class TrajectoryReIDTracker:
    def __init__(self, max_distance=150):
        self.next_object_id = 1
        self.objects = {}
        self.max_distance = max_distance
        self.historical_features = {}
        
    def update(self, rects):
        if len(rects) == 0: return self.objects
        input_centroids = []
        for (startX, startY, endX, endY) in rects:
            input_centroids.append((int((startX + endX) / 2.0), int((startY + endY) / 2.0)))
            
        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.objects[self.next_object_id] = input_centroids[i]
                self.historical_features[self.next_object_id] = [input_centroids[i]]
                self.next_object_id += 1
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())
            for ic in input_centroids:
                best_dist, best_id = float('inf'), None
                for o_id, o_c in zip(object_ids, object_centroids):
                    dist = math.sqrt((ic[0]-o_c[0])**2 + (ic[1]-o_c[1])**2)
                    if dist < best_dist: best_dist, best_id = dist, o_id
                if best_id is not None and best_dist < self.max_distance:
                    self.objects[best_id] = ic
                    self.historical_features[best_id].append(ic)
                else:
                    re_id_found = None
                    for h_id, h_c in self.historical_features.items():
                        if math.sqrt((ic[0]-h_c[-1][0])**2 + (ic[1]-h_c[-1][1])**2) < self.max_distance * 2:
                            re_id_found = h_id
                            break
                    if re_id_found is not None:
                        self.objects[re_id_found] = ic
                        self.historical_features[re_id_found].append(ic)
                    else:
                        self.objects[self.next_object_id] = ic
                        self.historical_features[self.next_object_id] = [ic]
                        self.next_object_id += 1
        return self.objects
