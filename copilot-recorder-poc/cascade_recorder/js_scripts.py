"""Holds JavaScript strings used by the recorder."""

# Event listener setup (master) – keeps MutationObserver for iframes
JS_EVENT_LISTENER_SCRIPT: str = r"""
if (window.CASCADE_LISTENERS_ACTIVE) {
    console.log('Cascade listeners already active.');
} else {
    window.CASCADE_LISTENERS_ACTIVE = true;
    window.recordedActions = []; // Initialize the global array
    console.log('Activating Cascade listeners.');

    window.getElementInfo = (el) => {
        if (!el) return null;
        return {
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            className: (el.className || '').substring(0, 200), // Truncate long class names
            name: el.getAttribute('name') || '',
            'aria-label': (el.getAttribute('aria-label') || '').substring(0, 100),
            innerText: (el.innerText || '').substring(0, 100).trim()
        };
    };

    window.cascadeClickListener = (e) => {
        if (!window.CASCADE_LISTENERS_ACTIVE) return;
        const action = {
            action_type: 'click',
            target_element: window.getElementInfo(e.target),
            timestamp: new Date().toISOString()
        };
        window.recordedActions.push(action);
    };

    window.cascadeInputListener = (e) => {
        if (!window.CASCADE_LISTENERS_ACTIVE) return;
        const action = {
            action_type: 'input',
            target_element: window.getElementInfo(e.target),
            input_text: e.target.value,
            timestamp: new Date().toISOString()
        };
        window.recordedActions.push(action);
    };

    window.cascadeKeyListener = (e) => {
        if (!window.CASCADE_LISTENERS_ACTIVE) return;
        if (e.key === 'Enter') {
            // Keep payload minimal to avoid truncation issues.
            const action = {
                action_type: 'key_press',
                key_pressed: 'Enter',
                timestamp: new Date().toISOString()
                // Target element info is intentionally omitted for key presses
                // as it's often less relevant and the primary cause of payload size issues.
            };
            window.recordedActions.push(action);
        }
    };

    const injectListenersIntoDoc = (doc) => {
        if (!doc || doc.cascadeListenersAttached) return;
        doc.addEventListener('click', window.cascadeClickListener, { capture: true });
        doc.addEventListener('input', window.cascadeInputListener, { capture: true });
        doc.addEventListener('keydown', window.cascadeKeyListener, { capture: true });
        doc.cascadeListenersAttached = true;
    };

    const setupIframe = (iframe) => {
        try {
            const contentDoc = iframe.contentDocument;
            if (contentDoc && contentDoc.readyState === 'complete') {
                injectListenersIntoDoc(contentDoc);
            } else {
                iframe.onload = () => injectListenersIntoDoc(iframe.contentDocument);
            }
        } catch (e) {
            console.warn('Cascade: Could not access iframe content.', iframe);
        }
    };

    injectListenersIntoDoc(document);
    document.querySelectorAll('iframe').forEach(setupIframe);

    window.cascadeObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) {
                    if (node.tagName === 'IFRAME') {
                        setupIframe(node);
                    } else if (node.querySelectorAll) {
                        node.querySelectorAll('iframe').forEach(setupIframe);
                    }
                }
            });
        });
    });

    window.cascadeObserver.observe(document.body, { childList: true, subtree: true });
    console.log('Cascade iframe observer is now active.');
}
"""

# Listener removal script
JS_REMOVE_LISTENERS_SCRIPT: str = r"""
if (window.CASCADE_LISTENERS_ACTIVE) {
    if (window.cascadeObserver) {
        window.cascadeObserver.disconnect();
        window.cascadeObserver = null;
    }

    const removeListenersFromDoc = (doc) => {
        if (!doc || !doc.cascadeListenersAttached) return;
        doc.removeEventListener('click', window.cascadeClickListener, { capture: true });
        doc.removeEventListener('input', window.cascadeInputListener, { capture: true });
        doc.removeEventListener('keydown', window.cascadeKeyListener, { capture: true });
        doc.cascadeListenersAttached = false;
    };

    document.querySelectorAll('iframe').forEach(iframe => {
        try { removeListenersFromDoc(iframe.contentDocument); } catch (e) {}
    });

    removeListenersFromDoc(document);
    window.CASCADE_LISTENERS_ACTIVE = false;
    console.log('All Cascade event listeners deactivated.');
}
"""