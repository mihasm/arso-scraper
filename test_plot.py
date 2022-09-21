import plotext as plt
import numpy as np


def plot_data():
	plt.plot([1,None,1,1,2],color="cyan")
	plt.title("test")
	plt.canvas_color("black")
	plt.axes_color("black")
	plt.ticks_color("white")
	plt.plot_size(plt.terminal_width(),40)
	plt.show()

plot_data()