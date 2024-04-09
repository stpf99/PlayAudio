import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, GObject, Gst, GLib
import os

# Inicjalizacja GStreamer
Gst.init(None)

class AudioPlayer(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Audio Player")

        self.set_default_size(1280, 720)
        self.connect("destroy", Gtk.main_quit)

        self.player = Gst.ElementFactory.make("playbin", "player")
        self.equalizer = Gst.ElementFactory.make("equalizer-3bands", "equalizer")

        self.playlist = Gtk.ListStore(str)
        self.treeview = Gtk.TreeView(model=self.playlist)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Playlist", renderer, text=0)
        self.treeview.append_column(column)
        self.treeview.connect("row-activated", self.on_row_activated)

        self.button_play = Gtk.Button(label="Play")
        self.button_play.connect("clicked", self.on_play_clicked)

        self.button_stop = Gtk.Button(label="Stop")
        self.button_stop.connect("clicked", self.on_stop_clicked)

        self.button_add = Gtk.Button(label="Add to Playlist")
        self.button_add.connect("clicked", self.on_add_clicked)

        self.button_load_folder = Gtk.Button(label="Load Folder")
        self.button_load_folder.connect("clicked", self.on_load_folder_clicked)

        self.slider_volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.slider_volume.set_value(50)
        self.slider_volume.connect("value-changed", self.on_volume_changed)

        self.equalizer_sliders = []
        for i in range(3):
            slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -24, 12, 1)
            slider.set_value(0)
            slider.connect("value-changed", self.on_eq_slider_changed, i)
            self.equalizer_sliders.append(slider)

        hbox_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox_buttons.pack_start(self.button_add, False, False, 0)
        hbox_buttons.pack_start(self.button_load_folder, False, False, 0)
        hbox_buttons.pack_start(self.button_play, False, False, 0)
        hbox_buttons.pack_start(self.button_stop, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.pack_start(self.treeview, True, True, 0)
        vbox.pack_start(hbox_buttons, False, False, 0)
        vbox.pack_start(Gtk.Label(label="Volume:"), False, False, 0)
        vbox.pack_start(self.slider_volume, False, False, 0)

        hbox_eq = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for i, slider in enumerate(self.equalizer_sliders):
            hbox_eq.pack_start(Gtk.Label(label=f"Band {i}"), False, False, 0)
            hbox_eq.pack_start(slider, True, True, 0)

        vbox.pack_start(hbox_eq, False, False, 0)

        self.add(vbox)

        self.current_playlist_index = -1

        # Podłączanie equalizera do odtwarzacza
        self.player.set_property("audio-filter", self.equalizer)

    def on_play_clicked(self, widget):
        if self.current_playlist_index != -1:
            self.player.set_state(Gst.State.PLAYING)

    def on_stop_clicked(self, widget):
        self.player.set_state(Gst.State.NULL)

    def on_add_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Please choose a file", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        filter_audio = Gtk.FileFilter()
        filter_audio.set_name("Audio files")
        filter_audio.add_mime_type("audio/*")
        dialog.add_filter(filter_audio)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.playlist.append([file_path])
        dialog.destroy()

    def on_load_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Please choose a folder", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.add_files_from_folder(folder_path)
        dialog.destroy()

    def add_files_from_folder(self, folder_path):
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".mp3") or file.endswith(".wav") or file.endswith(".ogg"):
                    file_path = os.path.join(root, file)
                    self.playlist.append([file_path])

    def on_row_activated(self, treeview, path, column):
        iter = treeview.get_model().get_iter(path)
        self.current_playlist_index = path.get_indices()[0]
        file_path = treeview.get_model().get_value(iter, 0)
        # Zwalnianie obecnego potoku, jeśli jest uruchomiony
        if self.player:
            self.player.set_state(Gst.State.NULL)
        self.player.set_property("uri", "file://" + file_path)
        self.player.set_state(Gst.State.PLAYING)

    def on_volume_changed(self, widget):
        volume = widget.get_value() / 100
        self.player.set_property("volume", volume)

    def on_eq_slider_changed(self, widget, band):
        value = widget.get_value()
        self.equalizer.set_property(f"band{band}", value)

    def run(self):
        self.show_all()
        Gtk.main()

if __name__ == "__main__":
    player = AudioPlayer()
    player.run()

