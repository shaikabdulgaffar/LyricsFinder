from django import forms

class LyricsForm(forms.Form):
    song_title = forms.CharField(label="Song Title", max_length=128, widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Enter song title...'}))
    artist_name = forms.CharField(label="Artist Name (optional)", max_length=128, required=False, widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Enter artist name (optional)'}))