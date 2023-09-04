import gi
import os
gi.require_version('GdkPixbuf', '2.0')
import gi.repository.GdkPixbuf as GdkPixbuf
gi.require_version('Gst', '1.0')
import gi.repository.Gst as Gst
gi.require_version('Gtk', '3.0')
import gi.repository.Gtk as Gtk
from urllib.parse import quote
import eyed3
import time
import random

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject

class MusicPlayer:
    def __init__(self):
        Gst.init(None)

        self.window = Gtk.Window()
        self.window.connect("destroy", Gtk.main_quit)
        self.window.set_default_size(800, 600)
        self.window.set_title("Music Player")

        self.playlist_store = Gtk.ListStore(str, str, str, str, str)
        self.playlist_view = Gtk.TreeView(self.playlist_store)
        self.playlist_view.set_rules_hint(True)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Playlist", renderer, text=0)
        self.playlist_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Artist", renderer, text=1)
        self.playlist_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Genre", renderer, text=2)
        self.playlist_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Album", renderer, text=3)
        self.playlist_view.append_column(column)

        column.set_sort_column_id(0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.playlist_view)

        self.play_button = Gtk.Button("Play")
        self.play_button.connect("clicked", self.play)
        self.pause_button = Gtk.Button("Pause")
        self.pause_button.connect("clicked", self.toggle_pause)
        self.stop_button = Gtk.Button("Stop")
        self.stop_button.connect("clicked", self.stop)

        self.load_from_dir_button = Gtk.Button("Load Dir")
        self.load_from_dir_button.connect("clicked", self.load_from_dir)
        self.append_from_file_button = Gtk.Button("Append File")
        self.append_from_file_button.connect("clicked", self.append_from_file)
        self.clear_playlist_button = Gtk.Button("Clear Playlist")
        self.clear_playlist_button.connect("clicked", self.clear_playlist)
        self.shuffle_playlist_button = Gtk.Button("Shuffle Playlist")
        self.shuffle_playlist_button.connect("clicked", self.shuffle_playlist)
        self.save_playlist_button = Gtk.Button("Save Playlist")
        self.save_playlist_button.connect("clicked", self.save_playlist)
        self.load_playlist_button = Gtk.Button("Load Playlist")
        self.load_playlist_button.connect("clicked", self.load_playlist)
        self.repeat_all_button = Gtk.ToggleButton("Repeat Playlist")
        self.repeat_all_button.connect("toggled", self.toggle_repeat_playlist)
        self.repeat_one_button = Gtk.ToggleButton("Repeat Current")
        self.repeat_one_button.connect("toggled", self.toggle_repeat_current)
        self.mute_button = Gtk.ToggleButton("Mute")
        self.mute_button.connect("toggled", self.toggle_mute)

        hbox_buttons = Gtk.HBox(False, 0)
        hbox_buttons.pack_start(self.play_button, True, True, 2)
        hbox_buttons.pack_start(self.pause_button, True, True, 2)
        hbox_buttons.pack_start(self.stop_button, True, True, 2)
        hbox_buttons.pack_start(self.load_from_dir_button, True, True, 2)
        hbox_buttons.pack_start(self.append_from_file_button, True, True, 2)
        hbox_buttons.pack_start(self.clear_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.shuffle_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.save_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.load_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.repeat_all_button, True, True, 2)
        hbox_buttons.pack_start(self.repeat_one_button, True, True, 2)
        hbox_buttons.pack_start(self.mute_button, True, True, 2)

        self.time_label = Gtk.Label("00:00:00 / 00:00:00")
        self.time_label.set_name("time-label")
        self.time_label.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))
        self.time_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        hbox_buttons.pack_start(self.time_label, False, False, 2)

        vbox = Gtk.VBox(False, 0)
        vbox.pack_start(scrolled_window, True, True, 2)
        vbox.pack_start(hbox_buttons, False, False, 2)

        # Dodaj suwak głośności
        self.gain_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.gain_scale.set_digits(0)
        self.gain_scale.set_value_pos(Gtk.PositionType.BOTTOM)
        self.gain_scale.add_mark(0, Gtk.PositionType.BOTTOM, "0%")
        self.gain_scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self.gain_scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        self.gain_scale.connect("value-changed", self.on_gain_scale_change)
        vbox.pack_start(self.gain_scale, False, False, 2)

        # Dodaj suwak pozycji
        self.position_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        self.position_scale.set_digits(0)
        self.position_scale.set_value_pos(Gtk.PositionType.BOTTOM)
        self.position_scale.add_mark(10, Gtk.PositionType.BOTTOM, "10%")
        self.position_scale.add_mark(20, Gtk.PositionType.BOTTOM, "20%")
        self.position_scale.add_mark(30, Gtk.PositionType.BOTTOM, "30%")
        self.position_scale.add_mark(40, Gtk.PositionType.BOTTOM, "40%")
        self.position_scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self.position_scale.add_mark(60, Gtk.PositionType.BOTTOM, "60%")
        self.position_scale.add_mark(70, Gtk.PositionType.BOTTOM, "70%")
        self.position_scale.add_mark(80, Gtk.PositionType.BOTTOM, "80%")
        self.position_scale.add_mark(90, Gtk.PositionType.BOTTOM, "90%")
        self.position_scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        self.position_scale.connect("value-changed", self.on_position_scale_change)
        vbox.pack_start(self.position_scale, False, False, 2)

        # Ustal aktualną pozycję suwaka na początku
        self.position_scale.set_value(0)

        self.window.add(vbox)
        self.window.show_all()

        self.pipeline = Gst.ElementFactory.make("playbin", "player")
        self.pipeline.set_property("volume", 1.0)
        self.playback_paused = False
        self.repeat_playlist = False
        self.repeat_current = False
        self.muted = False

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.update_time_timer = GObject.timeout_add(1000, self.update_time_label)

    def play(self, widget):
        selection = self.playlist_view.get_selection()
        model, selected_song_iter = selection.get_selected()

        if selected_song_iter:
            song_path = model.get_value(selected_song_iter, 0)
            self.play_audio_file(song_path)

    def play_audio_file(self, file_path):
        try:
            encoded_file_path = quote(file_path)
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.set_property("uri", f"file://{encoded_file_path}")
            self.pipeline.set_state(Gst.State.PLAYING)
            self.playback_paused = False
        except Exception as e:
            print(f"Error while playing audio: {e}")

    def toggle_pause(self, widget):
        if self.playback_paused:
            self.pipeline.set_state(Gst.State.PLAYING)
            self.playback_paused = False
        else:
            self.pipeline.set_state(Gst.State.PAUSED)
            self.playback_paused = True

    def stop(self, widget):
        self.pipeline.set_state(Gst.State.NULL)

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
        elif t == Gst.MessageType.EOS:
            if self.repeat_current:
                self.play_audio_file(self.pipeline.get_property("uri"))
            elif self.repeat_playlist:
                selection = self.playlist_view.get_selection()
                model, selected_song_iter = selection.get_selected()
                if selected_song_iter:
                    next_song_iter = model.iter_next(selected_song_iter)
                    if not next_song_iter:
                        next_song_iter = model.get_iter_first()
                    if next_song_iter:
                        next_song_path = model.get_value(next_song_iter, 0)
                        self.play_audio_file(next_song_path)
            else:
                self.pipeline.set_state(Gst.State.NULL)
                print("End-Of-Stream reached")

    def load_from_dir(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Please choose a directory", None, Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK)
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith((".mp3", ".wav", ".ogg", ".flac")):
                        song_path = os.path.join(root, file)
                        title, artist, genre, album = self.get_metadata_from_id3(song_path)
                        self.playlist_store.append([song_path, artist, genre, album, title])
        dialog.destroy()

    def append_from_file(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Please choose a file", None, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            song_path = dialog.get_filename()
            title, artist, genre, album = self.get_metadata_from_id3(song_path)
            self.playlist_store.append([song_path, artist, genre, album, title])
        dialog.destroy()

    def clear_playlist(self, widget):
        self.playlist_store.clear()

    def shuffle_playlist(self, widget):
        # Get the data from the ListStore and shuffle it
        playlist_data = [row[:] for row in self.playlist_store]
        random.shuffle(playlist_data)

        # Clear the ListStore and re-add the shuffled data
        self.playlist_store.clear()
        for row in playlist_data:
            self.playlist_store.append(row)

    def save_playlist(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Save Playlist", None, Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            playlist_file = dialog.get_filename()
            with open(playlist_file, "w") as f:
                for row in self.playlist_store:
                    f.write(f"{row[0]}\n")
        dialog.destroy()

    def load_playlist(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Load Playlist", None, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            playlist_file = dialog.get_filename()
            with open(playlist_file, "r") as f:
                lines = f.read().splitlines()
                for line in lines:
                    title, artist, genre, album = self.get_metadata_from_id3(line)
                    self.playlist_store.append([line, artist, genre, album, title])
        dialog.destroy()

    def toggle_repeat_playlist(self, widget):
        self.repeat_playlist = widget.get_active()

    def toggle_repeat_current(self, widget):
        self.repeat_current = widget.get_active()

    def toggle_mute(self, widget):
        self.muted = widget.get_active()
        if self.muted:
            self.pipeline.set_property("volume", 0.0)
        else:
            self.pipeline.set_property("volume", 1.0)

    def on_gain_scale_change(self, widget):
        value = self.gain_scale.get_value()
        volume = value / 100  # Przelicz wartość z zakresu 0-100 na zakres 0-1
        self.pipeline.set_property("volume", volume)

    def on_position_scale_change(self, widget):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            value = self.position_scale.get_value()
            position = (value / 100) * self.pipeline.query_duration(Gst.Format.TIME)[1]
            self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, position)

    def update_time_label(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            position, duration = self.pipeline.query_position(Gst.Format.TIME)[1], self.pipeline.query_duration(Gst.Format.TIME)[1]
            position_secs, duration_secs = position // Gst.SECOND, duration // Gst.SECOND
            position_str = time.strftime("%H:%M:%S", time.gmtime(position_secs))
            duration_str = time.strftime("%H:%M:%S", time.gmtime(duration_secs))
            self.time_label.set_text(f"{position_str} / {duration_str}")
            # Aktualizuj pozycję suwaka w czasie rzeczywistym
            if duration > 0:
                value = (position / duration) * 100
                self.position_scale.handler_block_by_func(self.on_position_scale_change)
                self.position_scale.set_value(value)
                self.position_scale.handler_unblock_by_func(self.on_position_scale_change)
        else:
            self.time_label.set_text("00:00:00 / 00:00:00")
        return True

    def get_metadata_from_id3(self, file_path):
        try:
            audiofile = eyed3.load(file_path)
            if audiofile and audiofile.tag:
                artist = str(audiofile.tag.artist)
                genre = str(audiofile.tag.genre)
                album = str(audiofile.tag.album)
                title = str(audiofile.tag.title)
                return title, artist, genre, album
        except Exception as e:
            print(f"Error reading ID3 tag: {e}")
        return os.path.basename(file_path), "", "", ""

if __name__ == "__main__":
    player = MusicPlayer()
    Gtk.main()

