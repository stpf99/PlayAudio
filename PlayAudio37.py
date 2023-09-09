import gi
import os
import random
import time
from urllib.parse import quote
import eyed3
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject
gi.require_version('GdkPixbuf', '2.0')
import gi.repository.GdkPixbuf as GdkPixbuf
gi.require_version('Gst', '1.0')
import gi.repository.Gst as Gst
import numpy as np
gi.require_version('Gtk', '3.0')
import pyaudio

class MusicPlayer:
    def __init__(self):
        Gst.init(None)

        self.window = Gtk.Window()
        self.window.connect("destroy", Gtk.main_quit)
        self.window.set_default_size(800, 600)
        self.window.set_title("Music Player")

        self.playlist_store = Gtk.ListStore(str, str, str, str, str)
        self.original_playlist = []  # Przechowuje oryginalną listę odtwarzania przed filtrowaniem
        self.playlist_view = Gtk.TreeView(self.playlist_store)
        self.playlist_view.set_rules_hint(True)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", renderer, text=4)
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

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Filename", renderer, text=0)  # Zmieniamy Label na "Filename"
        self.playlist_view.append_column(column)

        column.set_sort_column_id(4)

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

        self.now_playing_label = Gtk.Label()
        self.now_playing_label.set_name("now-playing-label")
        self.now_playing_label.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 1))
        self.now_playing_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        self.now_playing_label.set_markup('<span background="black" foreground="white" font_desc="12">Now Playing:</span>')

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search...")
        self.search_entry.connect("activate", self.search_playlist)

        # Dodaj rozwijalną listę dla typu wyszukiwania
        self.search_type_combo = Gtk.ComboBoxText()
        self.search_type_combo.append_text("Title")
        self.search_type_combo.append_text("Artist")
        self.search_type_combo.append_text("Genre")
        self.search_type_combo.append_text("Album")
        self.search_type_combo.set_active(0)  # Domyślnie wybierz "Title" jako typ wyszukiwania

        # Dodaj przycisk "Search"
        self.search_button = Gtk.Button("Search")
        self.search_button.connect("clicked", self.search_playlist)

        hbox_search = Gtk.HBox(False, 0)
        hbox_search.pack_start(self.search_type_combo, False, False, 2)  # Dodaj rozwijalną listę
        hbox_search.pack_start(self.search_entry, True, True, 2)
        hbox_search.pack_start(self.search_button, False, False, 2)
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.connect("draw", self.draw_spectrum)
        vbox = Gtk.VBox(False, 0)
        vbox.pack_start(self.now_playing_label, False, False, 2)
        vbox.pack_start(scrolled_window, True, True, 2)
        vbox.pack_start(hbox_buttons, False, False, 2)
        vbox.pack_start(hbox_search, False, False, 2)  # Dodaj pole wyszukiwania i przycisk "Search"

        # Add volume slider
        self.gain_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.gain_scale.set_digits(0)
        self.gain_scale.set_value_pos(Gtk.PositionType.BOTTOM)
        self.gain_scale.add_mark(0, Gtk.PositionType.BOTTOM, "0%")
        self.gain_scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self.gain_scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        self.gain_scale.connect("value-changed", self.on_gain_scale_change)
        vbox.pack_start(self.gain_scale, False, False, 2)

        # Add position slider
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
        self.fft_data = None
        # Add the progress bar
        self.progress_bar = Gtk.ProgressBar()
        vbox.pack_start(self.progress_bar, False, False, 2)

        # Set the initial position of the slider to 0
        self.position_scale.set_value(0)
        vbox.pack_start(self.drawing_area, True, True, 2)
        self.window.add(vbox)
        self.window.show_all()

        self.pipeline = Gst.ElementFactory.make("playbin", "player")
        self.pipeline.set_property("volume", 0.25)  # Set default volume to 25%
        self.playback_paused = False
        self.repeat_playlist = False
        self.repeat_one_enabled = False  # Initialize "Repeat Current" to False
        self.muted = False
        self.muted_volume = 0.25  # Set initial muted volume to 25%

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        # Update the "Now Playing" label in real-time
        self.update_now_playing_label()
        self.update_time_timer = GObject.timeout_add(1000, self.update_time_label)
        self.update_progress_bar_timer = GObject.timeout_add(1000, self.update_progress_bar)  # Add progress bar update timer
        self.pipeline = Gst.ElementFactory.make("playbin", "audio-player")
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos", self.on_eos)
        self.bus.connect("message::error", self.on_error)


        self.fft_data = None
        self.pipeline.set_state(Gst.State.READY)

        # Inicjalizacja PyAudio
        self.pa = pyaudio.PyAudio()
        self.stream = None


        # Ustalamy rozmiar paczki (chunk_size)
        self.chunk_size = 1024   # Przykładowy rozmiar paczki

    def draw_spectrum(self, widget, cr):
        if self.fft_data is not None:
            cr.set_source_rgb(255, 255, 255)
            cr.paint()

            num_bars = 256  # Liczba słupków
            bar_width = widget.get_allocated_width() / num_bars
            max_amplitude = np.max(self.fft_data)

            for i in range(num_bars):
                start = int((i / num_bars) * len(self.fft_data))
                end = int(((i + 1) / num_bars) * len(self.fft_data))
                bar_height = np.max(self.fft_data[start:end])
                bar_height /= max_amplitude  # Normalizacja do zakresu 0-1

                # Oblicz przezroczystość na podstawie wysokości słupka
                transparency = 0.01 + (bar_height * 0.5)
                
                # Nowa wysokość słupka - minimum 30% długości
                new_bar_height = bar_height
                
                color = (0, 0, 128)  # Kolor

                self.draw_bar(cr, i * bar_width, (1 - new_bar_height) * widget.get_allocated_height(), bar_width, new_bar_height * widget.get_allocated_height(), color, transparency)

    def draw_bar(self, cr, x, y, width, height, color, transparency):
        red, green, blue = color

        # Ustaw kolor słupka z określoną przezroczystością
        cr.set_source_rgba(0, 0, 128)
        cr.rectangle(x, y, width, height)
        cr.fill()

    def update_bars(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            query = Gst.Query.new_seeking(Gst.Format.TIME)
            if self.pipeline.query(query):
                _, position = self.pipeline.query_position(Gst.Format.TIME)
                _, duration = self.pipeline.query_duration(Gst.Format.TIME)
                progress = float(position) / float(duration) if duration > 0 else 0.0
                
                # Odczytaj dane audio z mikrofonu
                audio_data = self.read_audio_data()
                
                # Oblicz FFT na podstawie danych audio
                num_samples = 256  # Przykładowa liczba próbek
                fft_data = np.fft.fft(audio_data)
                fft_data = np.abs(fft_data[:num_samples])  # Pobierz amplitudy tylko pierwszych próbek
                
                self.fft_data = fft_data * progress
                GObject.idle_add(self.drawing_area.queue_draw)
        return True

    def read_audio_data(self):
        if self.stream is None:
            # Konfiguracja strumienia audio
            sample_rate = 44100  # Przykładowa częstotliwość próbkowania
            audio_format = pyaudio.paInt16

            self.stream = self.pa.open(
                format=audio_format,
                channels=1,  # Mono
                rate=sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size  # Używamy chunk_size jako rozmiar paczki
            )

        try:
            audio_data = self.stream.read(self.chunk_size)  # Używamy self.chunk_size
            audio_data = np.frombuffer(audio_data, dtype=np.int16)
            return audio_data
        except IOError as e:
            print("Błąd odczytu danych audio:", e)
            return np.zeros(self.chunk_size, dtype=np.int16) 


    def on_eos(self, bus, message):
        self.pipeline.set_state(Gst.State.READY)

    def on_error(self, bus, message):
        error, debug_info = message.parse_error()
        print("Error: %s" % error, debug_info)

   


    def on_gain_scale_change(self, widget):
        value = self.gain_scale.get_value()
        volume = value / 100  # Przelicz wartość z zakresu 0-100 na zakres 0-1
        self.pipeline.set_property("volume", volume)

    def play(self, widget):
        selection = self.playlist_view.get_selection()
        model, selected_song_iter = selection.get_selected()

        if selected_song_iter:
            song_path = model.get_value(selected_song_iter, 0)
            self.play_audio_file(song_path)
            GObject.timeout_add(100, self.update_bars)

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

    def on_position_scale_change(self, widget):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            value = self.position_scale.get_value()
            position = (value / 100) * self.pipeline.query_duration(Gst.Format.TIME)[1]
            self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, position)

    def update_position_slider(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            position, duration = self.pipeline.query_position(Gst.Format.TIME)[1], self.pipeline.query_duration(Gst.Format.TIME)[1]
            value = (position / duration) * 100
            self.position_scale.set_value(value)
        return True

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
        elif t == Gst.MessageType.EOS:
            if self.repeat_one_enabled:
                # Repeat the current song by seeking to the start
                self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
                self.pipeline.set_state(Gst.State.PLAYING)
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

        # Handle track change event
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                if new_state == Gst.State.PLAYING:
                    self.update_now_playing_label()
                    self.update_progress_bar()  # Start updating the progress bar

    def update_now_playing_label(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            selection = self.playlist_view.get_selection()
            model, selected_song_iter = selection.get_selected()
            if selected_song_iter:
                title = model.get_value(selected_song_iter, 4)
                artist = model.get_value(selected_song_iter, 1)
                self.now_playing_label.set_markup(
                    f'<span background="black" foreground="white" font_desc="12">Now Playing:</span> {artist} - {title}')

    def update_time_label(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            position, duration = self.pipeline.query_position(Gst.Format.TIME)[1], self.pipeline.query_duration(Gst.Format.TIME)[1]
            position_sec = position / Gst.SECOND
            duration_sec = duration / Gst.SECOND
            time_str = "{:02}:{:02}:{:02} / {:02}:{:02}:{:02}".format(
                int(position_sec // 3600),
                int((position_sec // 60) % 60),
                int(position_sec % 60),
                int(duration_sec // 3600),
                int((duration_sec // 60) % 60),
                int(duration_sec % 60),
            )
            self.time_label.set_text(time_str)
        return True

    def update_progress_bar(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            position, duration = self.pipeline.query_position(Gst.Format.TIME)[1], self.pipeline.query_duration(Gst.Format.TIME)[1]
            fraction = float(position) / float(duration)
            self.progress_bar.set_fraction(fraction)
        return True

    def load_from_dir(self, widget):
        dialog = Gtk.FileChooserDialog("Please choose a directory", self.window, Gtk.FileChooserAction.SELECT_FOLDER,
                                       ("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.load_music_from_folder(folder_path)
        dialog.destroy()

    def load_music_from_folder(self, folder_path):
        if folder_path:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(('.mp3', '.wav', '.flac')):
                        file_path = os.path.join(root, file)
                        self.append_song_to_playlist(file_path)

    def append_from_file(self, widget):
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window, Gtk.FileChooserAction.OPEN,
                                       ("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser("~"))

        filter_mp3 = Gtk.FileFilter()
        filter_mp3.set_name("MP3 files")
        filter_mp3.add_mime_type("audio/mpeg")
        dialog.add_filter(filter_mp3)

        filter_wav = Gtk.FileFilter()
        filter_wav.set_name("WAV files")
        filter_wav.add_mime_type("audio/wav")
        dialog.add_filter(filter_wav)

        filter_flac = Gtk.FileFilter()
        filter_flac.set_name("FLAC files")
        filter_flac.add_mime_type("audio/flac")
        dialog.add_filter(filter_flac)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.append_song_to_playlist(file_path)
        dialog.destroy()

    def append_song_to_playlist(self, file_path):
        audiofile = eyed3.load(file_path)
        title = audiofile.tag.title if audiofile.tag.title else os.path.basename(file_path)
        artist = audiofile.tag.artist if audiofile.tag.artist else "Unknown Artist"
        genre = str(audiofile.tag.genre) if audiofile.tag.genre else "Unknown Genre"
        album = audiofile.tag.album if audiofile.tag.album else "Unknown Album"
        filename = os.path.basename(file_path)

        self.playlist_store.append([file_path, artist, genre, album, title])
        self.original_playlist.append([file_path, artist, genre, album, title])

    def clear_playlist(self, widget):
        self.playlist_store.clear()
        self.original_playlist.clear()

    def shuffle_playlist(self, widget):
        random.shuffle(self.original_playlist)
        self.playlist_store.clear()
        for song in self.original_playlist:
            self.playlist_store.append(song)

    def save_playlist(self, widget):
        dialog = Gtk.FileChooserDialog("Save Playlist", self.window, Gtk.FileChooserAction.SAVE,
                                       ("Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser("~"))
        dialog.set_current_name("playlist.txt")

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.save_playlist_to_file(file_path)
        dialog.destroy()

    def save_playlist_to_file(self, file_path):
        with open(file_path, 'w') as f:
            for song in self.original_playlist:
                f.write(f"{song[0]}\n")

    def load_playlist(self, widget):
        dialog = Gtk.FileChooserDialog("Open Playlist", self.window, Gtk.FileChooserAction.OPEN,
                                       ("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser("~"))

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.load_playlist_from_file(file_path)
        dialog.destroy()

    def load_playlist_from_file(self, file_path):
        with open(file_path, 'r') as f:
            lines = f.read().splitlines()
            for line in lines:
                self.append_song_to_playlist(line)

    def toggle_repeat_playlist(self, widget):
        self.repeat_playlist = not self.repeat_playlist
        if self.repeat_playlist:
            self.repeat_one_button.set_active(False)

    def toggle_repeat_current(self, widget):
        self.repeat_one_enabled = not self.repeat_one_enabled
        if self.repeat_one_enabled:
            self.repeat_all_button.set_active(False)

    def toggle_mute(self, widget):
        if self.muted:
            # Restore the previous volume
            self.pipeline.set_property("volume", self.gain_scale.get_value() / 100)
        else:
            # Mute by setting the volume to 0
            self.pipeline.set_property("volume", 0)
        self.muted = not self.muted

    def search_playlist(self, widget):
        search_text = self.search_entry.get_text()
        search_type = self.search_type_combo.get_active_text()
        self.filter_playlist(search_text, search_type)

    def filter_playlist(self, search_text, search_type):
        self.playlist_store.clear()
        for song in self.original_playlist:
            if search_type == "Title" and search_text.lower() in song[4].lower():
                self.playlist_store.append(song)
            elif search_type == "Artist" and search_text.lower() in song[1].lower():
                self.playlist_store.append(song)
            elif search_type == "Genre" and search_text.lower() in song[2].lower():
                self.playlist_store.append(song)
            elif search_type == "Album" and search_text.lower() in song[3].lower():
                self.playlist_store.append(song)

if __name__ == "__main__":
    player = MusicPlayer()
    Gtk.main()

