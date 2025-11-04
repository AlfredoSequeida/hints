import St from 'gi://St';
import Main from 'resource:///org/gnome/shell/ui/main.js';

export default class HintsExtension {
    constructor() {
        this._widget = null;
    }

    enable() {
    }

    disable() {
    }
}

class Hints {
    // Returns [x, y, width, height, pid, name]
    // If no window is focused, returns [0, 0, 0, 0, -1, ""]
    FocusedWindowInfo() {
        const w = global.display.get_focus_window();
        if (!w) {
            return [0, 0, 0, 0, -1, ""];
        }
        const {x, y, width, height} = w.get_frame_rect();
        const pid = w.get_pid();
        const name = w.get_wm_class();
        return [x, y, width, height, pid, name];
    }
}
