import St from 'gi://St';
import Main from 'resource:///org/gnome/shell/ui/main.js';

export default class HintsExtension {
    constructor() {
        this._widget = null;
    }

    enable() {
        // Create a new St.Widget
        this._widget = new St.Bin({
            style_class: 'hints-widget',
            reactive: true,
            can_focus: true,
            track_hover: true
        });

        // Set the size of the widget to the full screen
        this._widget.set_size(global.screen_width, global.screen_height);

        // Set the opacity of the widget to make it transparent
        this._widget.set_opacity(128); // 0-255

        // Add the widget to the top layer of the UI
        Main.layoutManager.addChrome(this._widget, {
            affectsStruts: false,
            trackFullscreen: true
        });
    }

    disable() {
        if (this._widget) {
            Main.layoutManager.removeChrome(this._widget);
            this._widget.destroy();
            this._widget = null;
        }
    }
}