import tkinter as tk
from tkinter import ttk


class Point:
    """Простой класс для представления точки в 2D-пространстве."""
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"({self.x:.3f}, {self.y:.3f})"


class Clipper:
    """Класс для отсечения отрезков относительно прямоугольного окна."""

    INSIDE = 0
    LEFT = 1
    RIGHT = 2
    BOTTOM = 4
    TOP = 8

    def __init__(self, x_min, x_max, y_min, y_max):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

    def _compute_region_code(self, point):
        code = self.INSIDE
        if point.x < self.x_min:
            code |= self.LEFT
        elif point.x > self.x_max:
            code |= self.RIGHT
        if point.y < self.y_min:
            code |= self.BOTTOM
        elif point.y > self.y_max:
            code |= self.TOP
        return code

    def cohen_sutherland(self, p1, p2):
        """Алгоритм Коэна–Сазерленда."""
        code1 = self._compute_region_code(p1)
        code2 = self._compute_region_code(p2)

        while True:
            if code1 == 0 and code2 == 0:
                return [p1, p2]  # полностью внутри
            if code1 & code2:
                return None  # полностью вне

            # Выбираем внешнюю точку
            out_code = code1 if code1 != 0 else code2

            if out_code & self.TOP:
                x = p1.x + (p2.x - p1.x) * (self.y_max - p1.y) / (p2.y - p1.y)
                y = self.y_max
            elif out_code & self.BOTTOM:
                x = p1.x + (p2.x - p1.x) * (self.y_min - p1.y) / (p2.y - p1.y)
                y = self.y_min
            elif out_code & self.RIGHT:
                y = p1.y + (p2.y - p1.y) * (self.x_max - p1.x) / (p2.x - p1.x)
                x = self.x_max
            elif out_code & self.LEFT:
                y = p1.y + (p2.y - p1.y) * (self.x_min - p1.x) / (p2.x - p1.x)
                x = self.x_min
            else:
                x, y = p1.x, p1.y

            if out_code == code1:
                p1 = Point(x, y)
                code1 = self._compute_region_code(p1)
            else:
                p2 = Point(x, y)
                code2 = self._compute_region_code(p2)

    def midpoint_clip(self, p1, p2, tolerance=1e-5):
        """Алгоритм отсечения методом средней точки (рекурсивный приближённый)."""
        def in_window(pt):
            return self.x_min <= pt.x <= self.x_max and self.y_min <= pt.y <= self.y_max

        code1 = self._compute_region_code(p1)
        code2 = self._compute_region_code(p2)

        if code1 == 0 and code2 == 0:
            return [p1, p2]
        if code1 & code2:
            return None

        def find_intersection(a, b):
            for _ in range(50):
                mid = Point((a.x + b.x) / 2, (a.y + b.y) / 2)
                if in_window(mid):
                    a = mid
                else:
                    b = mid
                if abs(a.x - b.x) < tolerance and abs(a.y - b.y) < tolerance:
                    break
            return a

        if code1 == 0:
            inter = find_intersection(p1, p2)
            return [p1, inter]
        if code2 == 0:
            inter = find_intersection(p2, p1)
            return [p2, inter]

        # Обе точки вне, но отрезок пересекает окно
        inter1 = find_intersection(p1, p2)
        inter2 = find_intersection(p2, p1)
        if in_window(inter1) and in_window(inter2):
            return [inter1, inter2]
        return None


class Visualizer:
    """Класс для визуализации результатов отсечения."""
    def __init__(self, segments, clipper, cohen_results, midpoint_results):
        self.segments = segments
        self.clipper = clipper
        self.cohen = cohen_results
        self.midpoint = midpoint_results
        self.root = tk.Tk()
        self.root.title("Визуализация отсечения отрезков")
        self.root.geometry("1250x500")

        self._setup_ui()
        self._draw_all()

    def _map_to_canvas(self, x, y, canvas_w, canvas_h, margin=30):
        """Маппинг логических координат в пиксели."""
        pad = margin
        x_range = self.global_x_max - self.global_x_min
        y_range = self.global_y_max - self.global_y_min
        if x_range == 0: x_range = 1
        if y_range == 0: y_range = 1

        scale = min((canvas_w - 2*pad) / x_range, (canvas_h - 2*pad) / y_range)
        cx = pad + (x - self.global_x_min) * scale
        cy = canvas_h - (pad + (y - self.global_y_min) * scale)
        return cx, cy

    def _setup_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Определяем глобальные пределы для масштабирования
        all_x = [self.clipper.x_min, self.clipper.x_max]
        all_y = [self.clipper.y_min, self.clipper.y_max]
        for (p1, p2) in self.segments:
            all_x += [p1.x, p2.x]
            all_y += [p1.y, p2.y]
        self.global_x_min = min(all_x) - 0.1
        self.global_x_max = max(all_x) + 0.1
        self.global_y_min = min(all_y) - 0.1
        self.global_y_max = max(all_y) + 0.1

        self.canvases = []
        titles = ["Исходные данные", "Коэн–Сазерленд", "Средняя точка"]
        for i, title in enumerate(titles):
            frame = ttk.LabelFrame(top, text=title, padding=5)
            frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            canvas = tk.Canvas(frame, width=400, height=400, bg="white")
            canvas.pack()
            self.canvases.append(canvas)

    def _draw_window(self, canvas):
        x1, y1 = self._map_to_canvas(self.clipper.x_min, self.clipper.y_min, 400, 400)
        x2, y2 = self._map_to_canvas(self.clipper.x_max, self.clipper.y_max, 400, 400)
        canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)

    def _draw_segments(self, canvas, segments, clipped_list, base_color="gray"):
        colors = ["blue", "green", "purple", "orange", "brown", "pink"]
        for idx, (p1, p2) in enumerate(segments):
            cp1 = self._map_to_canvas(p1.x, p1.y, 400, 400)
            cp2 = self._map_to_canvas(p2.x, p2.y, 400, 400)

            # Исходный отрезок — серый пунктир
            canvas.create_line(cp1, cp2, fill=base_color, dash=(3, 3))

            # Отсечённый — цветной сплошной
            clipped = clipped_list[idx]
            if clipped:
                c1 = self._map_to_canvas(clipped[0].x, clipped[0].y, 400, 400)
                c2 = self._map_to_canvas(clipped[1].x, clipped[1].y, 400, 400)
                color = colors[idx % len(colors)]
                canvas.create_line(c1, c2, fill=color, width=3)
                canvas.create_oval(c1[0]-3, c1[1]-3, c1[0]+3, c1[1]+3, fill=color)
                canvas.create_oval(c2[0]-3, c2[1]-3, c2[0]+3, c2[1]+3, fill=color)

    def _draw_all(self):
        # Левый: исходные отрезки + окно
        self._draw_window(self.canvases[0])
        self._draw_segments(self.canvases[0], self.segments, [None]*len(self.segments))

        # Средний: результат Коэна–Сазерленда
        self._draw_window(self.canvases[1])
        self._draw_segments(self.canvases[1], self.segments, self.cohen)

        # Правый: результат метода средней точки
        self._draw_window(self.canvases[2])
        self._draw_segments(self.canvases[2], self.segments, self.midpoint)

    def run(self):
        self.root.mainloop()


def get_user_input():
    """Запрашивает у пользователя параметры окна и отрезков."""
    print("=== Отсечение отрезков ===")
    use_test = input("Использовать тестовые данные? (y/n): ").strip().lower() == 'y'

    if use_test:
        x_min, x_max = -1.0, 1.0
        y_min, y_max = -1.0, 1.0
        segments = [(Point(-1.5, 1/6), Point(0.5, 1.5))]
        print("Загружены тестовые данные.")
    else:
        print("\nВведите границы окна отсечения:")
        x_min = float(input("x_min (левая): "))
        x_max = float(input("x_max (правая): "))
        if x_min > x_max:
            x_min, x_max = x_max, x_min
        y_min = float(input("y_min (нижняя): "))
        y_max = float(input("y_max (верхняя): "))
        if y_min > y_max:
            y_min, y_max = y_max, y_min

        n = int(input("\nСколько отрезков ввести? "))
        segments = []
        for i in range(n):
            print(f"\nОтрезок #{i+1}:")
            x1 = float(input("  x1: ")); y1 = float(input("  y1: "))
            x2 = float(input("  x2: ")); y2 = float(input("  y2: "))
            segments.append((Point(x1, y1), Point(x2, y2)))

    return (x_min, x_max, y_min, y_max), segments


def main():
    window, segments = get_user_input()
    clipper = Clipper(*window)

    cohen_results = []
    midpoint_results = []

    print("\nРезультаты отсечения:")
    print("-" * 50)

    for i, (p1, p2) in enumerate(segments):
        c_res = clipper.cohen_sutherland(p1, p2)
        m_res = clipper.midpoint_clip(p1, p2)
        cohen_results.append(c_res)
        midpoint_results.append(m_res)

        print(f"\nОтрезок {i+1}: {p1} → {p2}")
        print(f"  Коэн–Сазерленд:    {'✓' if c_res else '✗'}")
        print(f"  Средняя точка:      {'✓' if m_res else '✗'}")

    print("\nЗапуск графической визуализации...")
    vis = Visualizer(segments, clipper, cohen_results, midpoint_results)
    vis.run()


if __name__ == "__main__":
    main()