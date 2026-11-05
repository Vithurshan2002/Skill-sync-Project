import { test, expect } from '@playwright/test';

test('registration errors appear under the correct fields and clear after correction', async ({ page }) => {
    await page.goto('/register');
    await page.getByLabel('Name', { exact: true }).fill('UI Test');
    await page.getByLabel('Email address', { exact: true }).fill('ui-only@example.com');
    const password = page.getByLabel('Password', { exact: true });
    const confirmation = page.getByLabel('Confirm password', { exact: true });
    const town = page.getByLabel('Town', { exact: true });
    await password.fill('Password-for-ui-test!');
    await confirmation.fill('Different-password!');
    await page.getByRole('button', { name: 'Create account', exact: true }).click();
    await expect(confirmation).toHaveAttribute('aria-invalid', 'true');
    await expect(town).toHaveAttribute('aria-invalid', 'true');
    await expect(password).not.toHaveAttribute('aria-invalid');
    await expect(page.locator('#password-confirmation-error')).toHaveText('The passwords do not match.');
    for (const input of [confirmation, town]) {
        expect(await input.evaluate(el => {
            const error = document.getElementById(el.getAttribute('aria-describedby'));
            return el.closest('.ss-field').contains(error) && error.getBoundingClientRect().top >= el.getBoundingClientRect().bottom;
        })).toBeTruthy();
        await expect(input).toHaveCSS('border-color', 'rgb(198, 84, 100)');
    }
    await expect(page.locator('.ss-auth-submit')).toBeEnabled();
    await confirmation.fill('Password-for-ui-test!');
    await town.selectOption('Colombo');
    await expect(confirmation).not.toHaveAttribute('aria-invalid');
    await expect(town).not.toHaveAttribute('aria-invalid');
    await expect(page.locator('#password-confirmation-error')).toHaveCount(0);
    await expect(page.locator('#town-error')).toHaveCount(0);
});

// Stop native navigation after the form's handlers run; no accounts or sessions are created.
for (const width of [1440, 390]) {
    for (const registration of [false, true]) {
        const path = registration ? '/register' : '/login';
        test(`${path} password controls and submission feedback at ${width}px`, async ({ page }) => {
            await page.setViewportSize({ width, height: 1000 });
            await page.goto(path);
            const submit = page.locator('.ss-auth-submit');
            const password = page.getByLabel('Password', { exact: true });
            const idleLabel = registration ? 'Create account' : 'Log in';
            const loadingLabel = registration ? 'Creating account…' : 'Logging in…';
            await page.evaluate(() => {
                window.authSubmissions = [];
                document.addEventListener('submit', event => {
                    if (event.defaultPrevented) return;
                    window.authSubmissions.push(Object.fromEntries(new FormData(event.target)));
                    event.preventDefault();
                });
            });

            await submit.click();
            await expect(submit).toBeEnabled();
            await expect(submit).toHaveText(idleLabel);
            expect(await page.evaluate(() => window.authSubmissions)).toHaveLength(0);

            await page.getByLabel('Email address', { exact: true }).fill('ui-only@example.com');
            await password.fill('Password-for-ui-test!');
            if (registration) {
                await page.getByLabel('Name', { exact: true }).fill('UI Test');
                await page.getByLabel('Town', { exact: true }).selectOption('Colombo');
                await page.getByLabel('Confirm password', { exact: true }).fill('Password-for-ui-test!');
            }
            await expect(password).toHaveAttribute('type', 'password');
            const toggle = page.getByRole('button', { name: 'Show password', exact: true });
            await expect(toggle.locator('[data-password-hidden-icon]')).toBeVisible();
            await expect(toggle.locator('[data-password-visible-icon]')).toBeHidden();
            await toggle.focus();
            await page.keyboard.press('Enter');
            await expect(password).toHaveAttribute('type', 'text');
            await expect(page.getByRole('button', { name: 'Hide password', exact: true }).locator('[data-password-visible-icon]')).toBeVisible();
            await expect(page.getByRole('button', { name: 'Hide password', exact: true }).locator('[data-password-hidden-icon]')).toBeHidden();
            await expect(password).toHaveValue('Password-for-ui-test!');
            if (registration) {
                const confirmation = page.getByLabel('Confirm password', { exact: true });
                await expect(confirmation).toHaveAttribute('type', 'password');
                await page.getByRole('button', { name: 'Show confirm password', exact: true }).click();
                await expect(confirmation).toHaveAttribute('type', 'text');
                await expect(page.getByRole('button', { name: 'Hide confirm password', exact: true }).locator('[data-password-visible-icon]')).toBeVisible();
                await page.getByRole('button', { name: 'Hide confirm password', exact: true }).click();
                await expect(confirmation).toHaveAttribute('type', 'password');
                await expect(page.getByRole('button', { name: 'Show confirm password', exact: true }).locator('[data-password-hidden-icon]')).toBeVisible();
            }
            await page.getByRole('button', { name: 'Hide password', exact: true }).click();
            await expect(password).toHaveAttribute('type', 'password');
            await expect(toggle.locator('[data-password-hidden-icon]')).toBeVisible();
            await page.getByRole('button', { name: 'Show password', exact: true }).click();
            const idleSize = await submit.boundingBox();
            expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();

            await submit.click();
            await expect(submit).toBeDisabled();
            await expect(submit).toHaveAttribute('aria-busy', 'true');
            await expect(submit).toHaveText(loadingLabel);
            await expect(password).toHaveAttribute('type', 'password');
            const loadingSize = await submit.boundingBox();
            expect(loadingSize.width).toBeCloseTo(idleSize.width, 0);
            expect(loadingSize.height).toBeCloseTo(idleSize.height, 0);
            expect(await submit.locator('[data-submit-label]').evaluate(el => getComputedStyle(el, '::before').animationName)).toBe('ss-busy-spin');
            await page.emulateMedia({ reducedMotion: 'reduce' });
            expect(await submit.locator('[data-submit-label]').evaluate(el => getComputedStyle(el, '::before').animationName)).toBe('none');
            await submit.evaluate(button => button.form.requestSubmit());
            const submissions = await page.evaluate(() => window.authSubmissions);
            expect(submissions).toHaveLength(1);
            expect(submissions[0].password).toBe('Password-for-ui-test!');
            if (registration) expect(submissions[0].password_confirmation).toBe('Password-for-ui-test!');

            await page.goto('/about');
            await page.goBack();
            await expect(submit).toBeEnabled();
            await expect(submit).toHaveText(idleLabel);
            await expect(password).toHaveAttribute('type', 'password');
        });
    }
}
