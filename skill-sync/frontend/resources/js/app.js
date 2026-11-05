// Livewire supplies Alpine; no second Alpine runtime is loaded.
document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('[aria-invalid="true"]')?.focus();
    document.querySelectorAll('.ss-auth-card form').forEach(form => {
        const password = form.querySelector('[name="password"]');
        const confirmation = form.querySelector('[name="password_confirmation"]');
        const updateConfirmation = () => {
            if (confirmation) confirmation.setCustomValidity(
                confirmation.value && confirmation.value !== password.value ? 'The passwords do not match.' : ''
            );
        };
        const renderError = input => {
            const field = input.closest('.ss-field');
            if (!field) return;
            const id = `${input.id}-error`;
            let error = document.getElementById(id);
            if (!error) {
                error = document.createElement('p');
                error.id = id;
                error.className = 'ss-field-error';
                field.append(error);
            }
            error.textContent = input.validationMessage;
            error.hidden = false;
            input.setAttribute('aria-invalid', 'true');
            input.setAttribute('aria-describedby', id);
        };
        form.addEventListener('invalid', event => {
            if (!event.target.matches('.ss-input')) return;
            event.preventDefault();
            renderError(event.target);
            form.querySelector('.ss-input:invalid')?.focus();
        }, true);
        form.querySelectorAll('.ss-input').forEach(input => {
            input.addEventListener('input', () => {
                updateConfirmation();
                for (const field of new Set([input, ...(input === password && confirmation ? [confirmation] : [])])) {
                    if (!field.hasAttribute('aria-invalid')) continue;
                    if (!field.validity.valid) {
                        renderError(field);
                        continue;
                    }
                    document.getElementById(`${field.id}-error`)?.remove();
                    field.removeAttribute('aria-invalid');
                    field.removeAttribute('aria-describedby');
                }
            });
        });
        updateConfirmation();
    });
    const passwordToggles = document.querySelectorAll('[data-password-toggle]');
    const setPasswordVisibility = (button, visible) => {
        const input = document.getElementById(button.getAttribute('aria-controls'));
        input.type = visible ? 'text' : 'password';
        button.setAttribute('aria-label', `${visible ? 'Hide' : 'Show'} ${button.dataset.passwordLabel}`);
        button.querySelector('[data-password-hidden-icon]').hidden = visible;
        button.querySelector('[data-password-visible-icon]').hidden = !visible;
    };
    passwordToggles.forEach(button => {
        button.hidden = false;
        button.addEventListener('click', () => {
            const input = document.getElementById(button.getAttribute('aria-controls'));
            setPasswordVisibility(button, input.type === 'password');
        });
    });
    document.querySelectorAll('[data-loading-label]').forEach(button => {
        button.dataset.idleLabel = button.querySelector('[data-submit-label]').textContent;
    });
    window.addEventListener('pageshow', () => {
        passwordToggles.forEach(button => setPasswordVisibility(button, false));
        document.querySelectorAll('[data-loading-label]').forEach(button => {
            button.disabled = false;
            button.removeAttribute('aria-busy');
            button.querySelector('[data-submit-label]').textContent = button.dataset.idleLabel;
            delete button.form.dataset.submitting;
        });
    });
    document.querySelectorAll('form[method="post"]:not([wire\\:submit])').forEach(form => {
        form.addEventListener('submit', event => {
            if (event.defaultPrevented || !form.checkValidity()) return;
            if (form.querySelector('[data-loading-label]')) {
                if (form.dataset.submitting) {
                    event.preventDefault();
                    return;
                }
                form.dataset.submitting = 'true';
                form.querySelectorAll('[data-password-toggle]').forEach(button => setPasswordVisibility(button, false));
            }
            form.querySelectorAll('button[type="submit"]').forEach(button => {
                button.disabled = true;
                button.setAttribute('aria-busy', 'true');
                if (button.dataset.loadingLabel) {
                    button.querySelector('[data-submit-label]').textContent = button.dataset.loadingLabel;
                }
            });
        });
    });
});
