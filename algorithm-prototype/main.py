from dijkstra import Graph

g = Graph(7)
g.add_vertex_data(0, "A")
g.add_vertex_data(1, "B")
g.add_vertex_data(2, "C")
g.add_vertex_data(3, "D")
g.add_vertex_data(4, "E")
g.add_vertex_data(5, "F")
g.add_vertex_data(6, "G")

g.add_edge(3, 0, 4)  # D - A, weight 5
g.add_edge(3, 4, 2)  # D - E, weight 2
g.add_edge(0, 2, 3)  # A - C, weight 3
g.add_edge(0, 4, 4)  # A - E, weight 4
g.add_edge(4, 2, 4)  # E - C, weight 4
g.add_edge(4, 6, 5)  # E - G, weight 5
g.add_edge(2, 5, 5)  # C - F, weight 5
g.add_edge(2, 1, 2)  # C - B, weight 2
g.add_edge(1, 5, 2)  # B - F, weight 2
g.add_edge(6, 5, 5)  # G - F, weight 5

# Dijkstra's algorithm from D to all vertices
print("\nDijkstra's Algorithm starting from vertex D:")
distance, path = g.dijkstra("D", "F")
print(f"Path: {path}, Distance: {distance}")

# for i, d in enumerate(distances):
#    path = g.get_path(predecessors, 'D', g.vertex_data[i])
#    print(f"{path}, Distance: {d}")
