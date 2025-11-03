
class Service {
    get _focusedWindow() {
        return global.display.get_focus_window();
    }

    FocusedWindowExtents() {
        const w = this._focusedWindow;
        if (!w) {
            return [0, 0, 0, 0];
        }
        const {x, y, width, height} = w.get_frame_rect();
        return [x, y, width, height];
    }

    FocusedWindowPid() {
        const w = this._focusedWindow;
        if (!w) {
            return -1;
        }
        return w.get_pid();
    }

    FocusedApplicationName() {
        return w.get_wm_class();
    }
}
