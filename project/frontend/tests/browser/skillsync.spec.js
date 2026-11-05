import { test, expect } from '@playwright/test';

const password = 'Integration-test-password!';
const backend = process.env.BACKEND_TEST_URL;
test.skip(!backend, 'Run through backend/tests/test_frontend_browser.py for an isolated PostgreSQL schema.');

async function register(page, role, name, email) {
    await page.goto('/register');
    await page.locator('input[name=role][value=' + role + ']').check();
    await page.getByLabel('Name', { exact: true }).fill(name);
    await page.getByLabel('Email address', { exact: true }).fill(email);
    await page.getByLabel('Town', { exact: true }).selectOption('Colombo');
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByLabel('Confirm password').fill(password);
    await page.getByRole('button', { name: 'Create account', exact: true }).click();
    await expect(page).toHaveURL(new RegExp('/' + role + '/'));
}

async function logout(page) {
    await page.goto('/settings');
    await page.getByRole('button', { name: 'Log out', exact: true }).click();
    await expect(page).toHaveURL(/\/$/);
}

async function login(page, email, loginPassword = password) {
    await page.goto('/login');
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password', { exact: true }).fill(loginPassword);
    await page.getByRole('button', { name: 'Log in', exact: true }).click({ noWaitAfter: true });
    await expect(page).toHaveURL(/\/(customer|worker|admin)\/dashboard/);
}

test('recommendation details and unread notifications are clear and responsive', async ({ page, request }) => {
    test.setTimeout(180000);
    async function api(method, path, data, token) {
        const response = await request[method](backend + '/api/v1' + path, {
            data, headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        expect(response.ok(), await response.text()).toBeTruthy();
        return (await response.json()).data;
    }
    const unique = Date.now();
    const worker = await api('post', '/auth/register', {
        role: 'worker', name: 'UI Test Professional', email: `ui-worker-${unique}@example.com`, password, town: 'Colombo',
    });
    const profile = await api('patch', '/worker/profile', {
        bio: 'Careful household tap and pipe repairs.', categories: ['Plumbing'], serviceTowns: ['Colombo'],
        yearsExperience: 5, rateLkr: 2500, rateUnit: 'visit', available: true,
    }, worker.accessToken);
    await login(page, `ui-worker-${unique}@example.com`);
    for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.goto('/worker/performance');
        await expect(page.getByRole('heading', { name: 'Category performance', exact: true })).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
        await page.screenshot({ path: `../../.integration-runtime/worker-performance-${width}.png`, fullPage: true, animations: 'disabled' });
    }
    await logout(page);
    await page.setViewportSize({ width: 1440, height: 1000 });
    await login(page, process.env.TEST_ADMIN_EMAIL, process.env.TEST_ADMIN_PASSWORD);
    await page.goto('/admin/notifications');
    await expect(page.locator('.ss-notification.is-unread')).toHaveCount(1);
    for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.reload();
        await expect(page.locator('.ss-notification.is-unread')).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
        await page.screenshot({ path: `../../.integration-runtime/unread-notifications-${width}.png`, animations: 'disabled' });
    }
    await page.getByRole('button', { name: 'Mark read', exact: true }).click();
    await expect(page.locator('.ss-notification.is-unread')).toHaveCount(0);
    await expect(page.locator('.ss-notification-read')).toBeVisible();
    await expect(page.locator('.ss-notification-count')).toHaveCount(0);
    await logout(page);
    const admin = await api('post', '/auth/login', { email: process.env.TEST_ADMIN_EMAIL, password: process.env.TEST_ADMIN_PASSWORD });
    await api('patch', `/admin/workers/${profile.id}/verification`, {
        verified: true, note: 'Profile checked in isolated UI testing.',
    }, admin.accessToken);
    const email = `ui-customer-${unique}@example.com`;
    const customer = await api('post', '/auth/register', { role: 'customer', name: 'UI Test Customer', email, password, town: 'Colombo' });
    const job = await api('post', '/requests', {
        title: 'Repair leaking kitchen tap', description: 'The kitchen tap leaks continuously when closed.',
        town: 'Colombo', category: 'Plumbing', preferredAt: new Date(Date.now() + 2 * 86400000).toISOString(),
    }, customer.accessToken);
    await login(page, email);
    for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.goto(`/customer/requests/${job.id}/recommendations`);
        const card = page.locator('.ss-recommendation').filter({ hasText: 'UI Test Professional' });
        await expect(card).toBeVisible();
        await page.screenshot({ path: `../../.integration-runtime/recommendation-page-${width}.png`, animations: 'disabled' });
        await expect(card.locator('.ss-reason-preview li')).toHaveCount(3);
        await expect(card.getByText('Provisional estimate', { exact: true })).toBeVisible();
        await expect(card.locator('.ss-reason-more')).toBeHidden();
        await card.locator('summary').click();
        await expect(card.locator('.ss-reason-more')).toBeVisible();
        await expect(card.getByText('Match score:', { exact: false })).toBeVisible();
        await card.locator('summary').click();
        await expect(card.locator('.ss-reason-more')).toBeHidden();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
        await card.screenshot({ path: `../../.integration-runtime/recommendation-summary-${width}.png`, animations: 'disabled' });
    }
});

test('workspace account pages keep role navigation on desktop and mobile', async ({ page, request }) => {
    test.setTimeout(180000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    for (const role of ['customer', 'worker', 'admin']) {
        const email = role === 'admin' ? process.env.TEST_ADMIN_EMAIL : `${role}-workspace-${Date.now()}@example.com`;
        if (role !== 'admin') {
            const response = await request.post(backend + '/api/v1/auth/register', {
                data: { role, email, password, name: `Workspace ${role}`, town: 'Colombo' },
            });
            expect(response.ok()).toBeTruthy();
        }
        await page.setViewportSize({ width: 1440, height: 1000 });
        await login(page, email, role === 'admin' ? process.env.TEST_ADMIN_PASSWORD : password);
        for (const slug of ['notifications', 'settings']) {
            await page.goto('/' + slug);
            await expect(page).toHaveURL(new RegExp(`/${role}/${slug}$`));
            await expect(page.getByRole('heading', {
                name: slug === 'settings' ? 'Account settings' : 'Notifications', exact: true,
            })).toBeVisible();
            await expect(page.locator(`.fi-sidebar-item.fi-active a[href$="/${role}/${slug}"]`)).toBeVisible();
            await expect(page.locator('.ss-notification-bell a')).toHaveAttribute('href', new RegExp(`/${role}/notifications$`));
            await expect(page.getByRole('navigation', { name: 'Main navigation' })).toHaveCount(0);
            if (slug === 'settings') {
                await expect(page.getByRole('link', { name: 'Edit profile', exact: true })).toHaveCount(role === 'admin' ? 0 : 1);
                await expect(page.getByRole('button', { name: 'Log out', exact: true })).toBeVisible();
            } else {
                await page.getByRole('button', { name: /^Unread/ }).click();
                await expect(page.getByRole('button', { name: /^Unread/ })).toHaveClass(/is-active/);
            }
            for (const width of [1440, 390]) {
                await page.setViewportSize({ width, height: 1000 });
                await page.reload();
                await expect(page.getByRole('heading', {
                    name: slug === 'settings' ? 'Account settings' : 'Notifications', exact: true,
                })).toBeVisible();
                if (width === 390) {
                    await page.locator('.fi-topbar-open-sidebar-btn').click();
                    await expect(page.locator(`.fi-sidebar-item.fi-active a[href$="/${role}/${slug}"]`)).toBeVisible();
                    await page.locator('.fi-sidebar-close-overlay').click({ position: { x: 380, y: 500 } });
                    await expect(page.locator('.fi-sidebar-close-overlay')).toBeHidden();
                    await expect(page.locator('.fi-topbar-open-sidebar-btn')).toBeVisible();
                }
                expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
                await page.screenshot({ path: `../../.integration-runtime/workspace-${role}-${slug}-${width}.png`, animations: 'disabled' });
            }
            await page.setViewportSize({ width: 1440, height: 1000 });
        }
        await logout(page);
        await page.goto(`/${role}/settings`);
        await expect(page).toHaveURL(/\/login$/);
    }
    expect(errors).toEqual([]);
});

test('real registration, worker profile, request, booking, completion and review', async ({ page, request }) => {
    test.setTimeout(300000);
    // Initial model-backed pages can exceed 15 seconds on the local PHP test server.
    page.setDefaultTimeout(30000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const unique = Date.now();
    const workerEmail = 'worker-' + unique + '@example.com';
    const customerEmail = 'customer-' + unique + '@example.com';
    const workerName = 'Browser Plumber ' + unique;
    await register(page, 'worker', workerName, workerEmail);
    await expect(page).toHaveURL(/\/worker\/profile/);
    const map = page.getByRole('region', { name: 'Location map', exact: true });
    await expect(map.locator('.leaflet-control-zoom')).toBeVisible();
    await expect(map.locator('.ss-map-marker')).toHaveCount(0);
    await expect(page.getByLabel('Latitude', { exact: true })).toBeEmpty();
    // One explicit public-place lookup exercises the real proxy, CSRF and provider.
    await page.getByLabel('Search address or place in Sri Lanka', { exact: true }).fill('Colombo');
    const searchResponse = page.waitForResponse(response => response.url().endsWith('/locations/search'));
    await page.getByRole('button', { name: 'Search address', exact: true }).click();
    expect((await searchResponse).status()).toBe(200);
    await expect(page.locator('.ss-address-results button').first()).toBeVisible();
    await page.locator('.ss-address-results button').first().click();
    await expect(page.getByLabel('Latitude', { exact: true })).not.toBeEmpty();
    await page.getByRole('button', { name: 'Clear location', exact: true }).click();
    let addressCalls = 0;
    const addressMock = async route => {
        addressCalls++;
        const query = route.request().postDataJSON().query;
        if (query === 'Unavailable') return route.fulfill({ status: 503, json: { message: 'Unavailable' } });
        return route.fulfill({ json: { data: query === 'Unknown landmark' ? [] : [
            { label: 'Colombo Fort, Sri Lanka', latitude: 6.9344, longitude: 79.8428 },
            { label: 'Colombo, Sri Lanka', latitude: 6.9271, longitude: 79.8612 },
        ] } });
    };
    await page.route('**/locations/search', addressMock);
    const addressInput = page.getByLabel('Search address or place in Sri Lanka', { exact: true });
    await addressInput.fill('Colombo Fort');
    expect(addressCalls).toBe(0);
    await addressInput.press('Enter');
    await expect(page.getByRole('button', { name: 'Colombo Fort, Sri Lanka', exact: true })).toBeVisible();
    await expect(page.getByLabel('Latitude', { exact: true })).toBeEmpty();
    await page.getByRole('button', { name: 'Colombo Fort, Sri Lanka', exact: true }).click();
    await expect(page.getByLabel('Latitude', { exact: true })).toHaveValue('6.9344');
    await expect(map.locator('.ss-map-marker')).toBeVisible();
    await addressInput.fill('Unknown landmark');
    await page.getByRole('button', { name: 'Search address', exact: true }).click();
    await expect(page.getByText('No places found.', { exact: false })).toBeVisible();
    await expect(page.getByLabel('Latitude', { exact: true })).toHaveValue('6.9344');
    await addressInput.fill('Unavailable');
    await addressInput.press('Enter');
    await expect(page.getByText('Address search is unavailable.', { exact: false })).toBeVisible();
    await page.getByRole('button', { name: 'Clear location', exact: true }).click();
    await expect(addressInput).toBeEmpty();
    await page.unroute('**/locations/search', addressMock);
    await expect(map.locator('.ss-map-marker')).toHaveCount(0);
    await page.route('https://tile.openstreetmap.org/**', route => route.abort());
    await page.reload();
    await expect(page.getByText('Map imagery could not load.', { exact: false })).toBeVisible();
    await page.evaluate(() => Object.defineProperty(navigator, 'geolocation', { configurable: true,
        value: { getCurrentPosition: (success, error) => error({ code: 1 }) } }));
    await page.getByRole('button', { name: 'Use current location', exact: true }).click();
    await expect(page.getByText('Location permission was denied.', { exact: false })).toBeVisible();
    await expect(page.getByLabel('Latitude', { exact: true })).toBeEmpty();
    await map.click({ position: { x: 140, y: 120 } });
    await expect(map.locator('.ss-map-marker')).toBeVisible();
    await expect(page.getByLabel('Latitude', { exact: true })).not.toBeEmpty();
    await page.getByRole('button', { name: 'Clear location', exact: true }).click();
    await expect(map.locator('.ss-map-marker')).toHaveCount(0);
    await page.unroute('https://tile.openstreetmap.org/**');
    await page.reload();
    await page.context().grantPermissions(['geolocation']);
    await page.context().setGeolocation({ latitude: 7, longitude: 80, accuracy: 20 });
    await page.getByRole('button', { name: 'Use current location', exact: true }).click();
    await expect(page.getByLabel('Latitude', { exact: true })).toHaveValue('7');
    await expect(page.getByLabel('Longitude', { exact: true })).toHaveValue('80');
    await page.getByLabel('Service radius (km)', { exact: true }).fill('20');
    await expect(map.locator('.leaflet-overlay-pane path')).toBeVisible();
    const pin = map.locator('.ss-map-marker');
    await pin.scrollIntoViewIfNeeded();
    const pinBox = await pin.boundingBox();
    await page.mouse.move(pinBox.x + 15, pinBox.y + 14);
    await page.mouse.down();
    await page.mouse.move(pinBox.x + 65, pinBox.y + 34, { steps: 8 });
    await page.mouse.up();
    await expect(page.getByLabel('Longitude', { exact: true })).not.toHaveValue('80');
    await page.getByRole('button', { name: 'Use current location', exact: true }).click();
    await expect(page.getByLabel('Longitude', { exact: true })).toHaveValue('80');
    await map.screenshot({ path: '../../.integration-runtime/location-map-desktop.png' });

    await page.getByLabel('About your work').fill('Careful household tap and pipe repairs in Colombo.');
    await page.getByLabel('Plumbing', { exact: true }).check();
    await page.getByLabel('Towns you serve').fill('Colombo');
    await page.getByLabel('Towns you serve').press('Enter');
    await page.getByLabel('Years of experience').fill('5');
    await page.getByLabel('Service rate').fill('2500');
    await page.getByRole('switch', { name: 'Available for new jobs' }).click();
    await page.getByRole('button', { name: 'Save profile', exact: true }).click();
    await expect(page.locator('.ss-profile-save-actions [role=status]')).toHaveText('Request sent. Waiting for admin approval.');
    await expect(page.getByText('Your profile has been updated.', { exact: true })).toHaveCount(0);
    await page.reload();
    await expect(page.getByLabel('Service rate')).toHaveValue('2500');
    await expect(page.getByLabel('Latitude', { exact: true })).toHaveValue('7');
    await expect(page.getByLabel('Service radius (km)', { exact: true })).toHaveValue('20');
    await page.setViewportSize({ width: 360, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await page.getByRole('button', { name: 'Use current location', exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: '../../.integration-runtime/gps-worker-mobile.png' });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await expect(page.locator('.ss-profile-save-actions [role=status]')).toHaveText('Request sent. Waiting for admin approval.');
    await expect(page.getByRole('button', { name: 'Save profile', exact: true })).toBeVisible();
    const hidden = await request.get(backend + '/api/v1/workers', { params: { search: workerName } });
    expect((await hidden.json()).data).toEqual([]);
    await logout(page);

    await login(page, process.env.TEST_ADMIN_EMAIL, process.env.TEST_ADMIN_PASSWORD);
    const pendingApplications = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Pending worker applications', exact: true }) });
    await expect(pendingApplications.locator('strong')).toHaveText('1');
    await expect(page.locator('.ss-notification-bell .ss-notification-count')).toHaveText('1');
    await page.getByRole('link', { name: 'Review pending applications' }).click();
    await expect(page.getByRole('checkbox', { name: 'Ready for approval only' })).toBeChecked();
    await expect(page.locator('.fi-ta tbody tr')).toHaveCount(1);
    await page.goto('/notifications');
    const newApplication = page.getByRole('link', { name: 'Worker application ready for review: ' + workerName, exact: false });
    await expect(newApplication).toBeVisible();
    await expect(page.locator('.ss-notification-bell .ss-notification-count')).toHaveText('1');
    await expect(newApplication).toContainText('Changed:');
    await page.locator('article').filter({ has: newApplication }).getByRole('button', { name: 'Mark read', exact: true }).click();
    await expect(page.locator('article').filter({ has: newApplication })).toContainText('Read');
    await expect(page.locator('.ss-notification-bell .ss-notification-count')).toHaveCount(0);
    await expect(page.locator('.ss-notification-bell a')).toHaveAttribute('aria-label', 'Notifications, 0 unread');
    await newApplication.click();
    await expect(page).toHaveURL(/detailTab=changes/);
    await expect(page.getByRole('button', { name: 'Change requests', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByRole('region', { name: 'Profile details', exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: 'Profile details', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Profile details', exact: true })).toBeVisible();
    await page.locator('.ss-worker-record').screenshot({ path: '../../.integration-runtime/admin-profile-desktop.png' });
    await page.setViewportSize({ width: 360, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await page.locator('.ss-worker-record').screenshot({ path: '../../.integration-runtime/admin-profile-mobile.png' });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await expect(page.getByRole('region', { name: 'Profile changes', exact: true })).toHaveCount(0);
    const reviewApplication = page.getByRole('button', { name: 'Review application', exact: true });
    await expect(reviewApplication).toHaveCount(1);
    await expect(reviewApplication).toBeVisible();
    await expect(page.getByRole('button', { name: 'Review changes', exact: true })).toHaveCount(0);
    await reviewApplication.click();
    await expect(page.getByRole('alertdialog').getByRole('heading', { name: 'Review worker application', exact: true })).toBeVisible();
    await page.getByRole('alertdialog').getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(page.getByRole('alertdialog')).toHaveCount(0);
    await page.getByRole('button', { name: 'Change requests', exact: true }).click();
    await expect(reviewApplication).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Review changes', exact: true })).toBeVisible();
    await expect(page.getByRole('region', { name: 'Experience change', exact: true })).toContainText('5');
    await expect(page.getByRole('region', { name: 'Experience change', exact: true })).toContainText('0');
    await page.locator('.ss-worker-record').screenshot({ path: '../../.integration-runtime/admin-changes-desktop.png' });
    await page.setViewportSize({ width: 360, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await page.locator('.ss-worker-record').screenshot({ path: '../../.integration-runtime/admin-changes-mobile.png' });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole('button', { name: 'Review changes', exact: true }).click();
    let approval = page.getByRole('alertdialog');
    await approval.getByLabel('Decision', { exact: false }).selectOption('changes');
    await approval.getByLabel('Feedback for worker').fill('Please describe the pipe repairs you provide.');
    await approval.getByRole('button', { name: 'Save decision', exact: true }).click();
    await expect(approval).toHaveCount(0);
    await page.goto('/admin/dashboard');
    await expect(pendingApplications.locator('strong')).toHaveText('0');
    await logout(page);
    await login(page, workerEmail);
    await page.goto('/worker/profile');
    await expect(page.locator('.ss-profile-save-actions [role=status]')).toContainText('Changes requested.');
    await expect(page.getByText('Please describe the pipe repairs you provide.', { exact: false })).toBeVisible();
    await page.getByLabel('About your work').fill('I repair leaking household pipes and replace damaged tap fittings.');
    await page.getByRole('button', { name: 'Save profile', exact: true }).click();
    await expect(page.locator('.ss-profile-save-actions [role=status]')).toHaveText('Request sent. Waiting for admin approval.');
    await expect(page.getByRole('button', { name: 'Save profile', exact: true })).toBeVisible();
    await logout(page);
    await login(page, process.env.TEST_ADMIN_EMAIL, process.env.TEST_ADMIN_PASSWORD);
    await expect(pendingApplications.locator('strong')).toHaveText('1');
    await page.goto('/notifications');
    await page.getByRole('link', { name: 'Worker application resubmitted: ' + workerName, exact: false }).click();
    await page.getByRole('button', { name: 'Review changes', exact: true }).click();
    approval = page.getByRole('alertdialog');
    await approval.getByLabel('Decision', { exact: false }).selectOption('approve');
    await approval.getByLabel('Feedback for worker').fill('Completed profile checked in isolated browser testing.');
    await approval.getByRole('button', { name: 'Save decision', exact: true }).click();
    await expect(approval).toHaveCount(0);
    await page.goto('/admin/dashboard');
    await expect(pendingApplications.locator('strong')).toHaveText('0');
    await logout(page);

    await register(page, 'customer', 'Browser Customer ' + unique, customerEmail);
    await page.goto('/customer/requests/new');
    await expect(page.getByRole('button', { name: 'Use current location', exact: true })).toHaveCount(0);
    await page.getByLabel('Latitude', { exact: true }).fill('7.01');
    await page.getByLabel('Longitude', { exact: true }).fill('80');
    await expect(page.getByLabel('Latitude', { exact: true })).toHaveValue('7.01');
    await page.getByRole('button', { name: 'Clear location', exact: true }).click();
    await expect(page.getByLabel('Latitude', { exact: true })).toBeEmpty();
    await expect(page.getByLabel('Longitude', { exact: true })).toBeEmpty();
    await page.getByLabel('Latitude', { exact: true }).fill('7.01');
    await page.getByLabel('Longitude', { exact: true }).fill('80');
    await expect(page.getByLabel('Latitude', { exact: true })).toHaveValue('7.01');

    await page.getByLabel('Give your request a title').fill('Repair the browser test kitchen tap');
    await page.getByLabel('Tell us about the job').fill('The kitchen tap leaks continuously even when it is closed.');
    const future = new Date(Date.now() + 4 * 86400000);
    const appointment = future.toISOString().slice(0, 10) + 'T10:00';
    await page.getByLabel('Preferred date and time').fill(appointment);
    await page.getByRole('button', { name: 'Save and continue', exact: true }).click();
    await expect(page).toHaveURL(/\/customer\/requests\/[a-f0-9-]+$/);
    const requestId = new URL(page.url()).pathname.split('/').at(-1);
    await page.getByRole('button', { name: 'Edit request', exact: true }).click();
    const locationDialog = page.getByRole('dialog');
    await expect(locationDialog.getByLabel('Latitude', { exact: true })).toHaveValue('7.01');
    await page.route('**/locations/search', addressMock);
    await locationDialog.getByLabel('Search address or place in Sri Lanka', { exact: true }).fill('Colombo Fort');
    await locationDialog.getByRole('button', { name: 'Search address', exact: true }).click();
    await locationDialog.getByRole('button', { name: 'Colombo Fort, Sri Lanka', exact: true }).click();
    await expect(locationDialog.getByLabel('Longitude', { exact: true })).toHaveValue('79.8428');
    await page.unroute('**/locations/search', addressMock);
    const modalMap = locationDialog.getByRole('region', { name: 'Location map', exact: true });
    await expect(modalMap.locator('.ss-map-marker')).toBeVisible();
    await modalMap.click({ position: { x: 180, y: 100 } });
    const selectedLatitude = await locationDialog.getByLabel('Latitude', { exact: true }).inputValue();
    const selectedLongitude = await locationDialog.getByLabel('Longitude', { exact: true }).inputValue();
    expect(selectedLatitude).not.toBe('7.01');
    await locationDialog.getByRole('button', { name: 'Save changes', exact: true }).click();
    await expect(locationDialog).toHaveCount(0);
    await page.reload();
    await page.getByRole('button', { name: 'Edit request', exact: true }).click();
    await expect(locationDialog.getByLabel('Latitude', { exact: true })).toHaveValue(selectedLatitude);
    await expect(locationDialog.getByLabel('Longitude', { exact: true })).toHaveValue(selectedLongitude);
    await expect(modalMap.locator('.ss-map-marker')).toBeVisible();
    await modalMap.focus();
    await page.keyboard.press('ArrowRight');
    await locationDialog.getByRole('button', { name: 'Use map centre', exact: true }).click();
    await expect(locationDialog.getByLabel('Longitude', { exact: true })).not.toHaveValue(selectedLongitude);
    await expect(locationDialog.getByRole('button', { name: 'Use current location', exact: true })).toHaveCount(0);
    await locationDialog.getByLabel('Latitude', { exact: true }).fill('7.02');
    await locationDialog.getByLabel('Longitude', { exact: true }).fill('80');
    await expect(locationDialog.getByLabel('Latitude', { exact: true })).toHaveValue('7.02');
    await locationDialog.getByRole('button', { name: 'Save changes', exact: true }).click();
    await expect(locationDialog).toHaveCount(0);

    await page.getByRole('button', { name: 'Find suitable workers' }).click();
    await expect(page).toHaveURL(/\/recommendations/);
    const category = page.getByRole('combobox', { name: 'Service category', exact: true });
    await expect(category).toHaveValue('Plumbing');
    await expect(category.locator('option')).toHaveCount(5);
    await expect(page.getByText('AI suggested Plumbing.', { exact: false })).toBeVisible();
    const card = page.locator('.ss-recommendation').filter({ hasText: workerName });
    await expect(card).toBeVisible();
    await expect(card.locator('.ss-distance-label')).toContainText('2.2 km away');
    await expect(card).toContainText('within this worker');
    await expect(card).toContainText('limited work history.');
    await expect(page.getByText('AI ranked matches', { exact: true })).toBeVisible();
    await card.getByRole('checkbox', { name: 'Compare' }).check();
    await expect(page.locator('.ss-comparison')).toBeVisible();
    await card.getByRole('button', { name: 'Choose professional' }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('Expected end time').fill(future.toISOString().slice(0, 10) + 'T12:00');
    await dialog.getByLabel('Set a different deadline', { exact: true }).check();
    await dialog.getByLabel('Completion deadline').fill(future.toISOString().slice(0, 10) + 'T18:00');
    await dialog.getByRole('checkbox', { name: 'I understand the rate basis and want to request this booking.' }).check();
    await dialog.getByRole('button', { name: 'Confirm booking', exact: true }).click();
    await expect(page).toHaveURL(/\/customer\/bookings\/[a-f0-9-]+$/);
    const bookingId = new URL(page.url()).pathname.split('/').at(-1);
    await expect(page.locator('.ss-status-pending').first()).toBeVisible();
    await logout(page);

    await login(page, workerEmail);
    expect((await page.goto('/customer/dashboard')).status()).toBe(403);
    await page.goto('/worker/jobs/' + bookingId);
    for (const label of ['Accept job', 'Start job', 'Request completion confirmation']) {
        await page.getByRole('button', { name: label, exact: true }).click();
        const confirmation = page.getByRole('alertdialog');
        await confirmation.getByRole('button', { name: 'Confirm', exact: true }).click();
        await expect(confirmation).toHaveCount(0);
    }
    await expect(page.locator('.ss-status-awaiting-confirmation').first()).toBeVisible();
    await logout(page);
    await login(page, customerEmail);
    await page.goto('/customer/bookings/' + bookingId);
    await page.getByRole('button', { name: 'Confirm completed', exact: true }).click();
    await page.getByRole('alertdialog').getByRole('button', { name: 'Confirm', exact: true }).click();
    await expect(page.locator('.ss-status-completed').first()).toBeVisible();
    await page.getByRole('button', { name: 'Leave a review', exact: true }).click();
    const review = page.getByRole('dialog');
    await review.getByLabel('Rating').selectOption('5');
    await review.getByLabel('Your review').fill('Careful repairs and clear communication throughout the job.');
    await review.getByRole('button', { name: 'Submit', exact: true }).click();
    await expect(review).toHaveCount(0);
    await page.reload();
    await expect(page.getByText('Careful repairs and clear communication throughout the job.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Leave a review', exact: true })).toHaveCount(0);
    await page.goto('/notifications');
    await expect(page.locator('h1')).toBeVisible();

    const response = await request.post(backend + '/api/v1/auth/login', { data: { email: customerEmail, password } });
    expect(response.ok()).toBeTruthy();
    const token = (await response.json()).data.accessToken;
    const saved = await request.get(backend + '/api/v1/bookings/' + bookingId, { headers: { Authorization: 'Bearer ' + token } });
    const record = (await saved.json()).data;
    expect(record.status).toBe('completed');
    expect(record.review.rating).toBe(5);
    expect(record.requestId).toBe(requestId);
    // The form's 10:00 Colombo appointment must arrive as 04:30 UTC.
    expect(record.scheduledAt.slice(11, 16)).toBe('04:30');
    expect(record.deadlineAt.slice(11, 16)).toBe('12:30');
    await page.goto('/customer/bookings/' + bookingId);
    await page.getByRole('button', { name: 'Submit complaint', exact: true }).click();
    const complaint = page.getByRole('dialog');
    await complaint.getByLabel('Describe the issue and supporting details').fill('The repaired pipe is leaking again after the visit.');
    await complaint.getByRole('button', { name: 'Submit', exact: true }).click();
    await expect(complaint).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Complaint: Pending' })).toBeVisible();
    await logout(page);
    await login(page, workerEmail);
    await page.goto('/worker/performance');
    await expect(page.getByText('1 completed jobs').first()).toBeVisible();
    await logout(page);
    await login(page, process.env.TEST_ADMIN_EMAIL, process.env.TEST_ADMIN_PASSWORD);
    await page.goto('/admin/records?entity=complaints');
    await page.locator('.fi-ta tbody tr').first().getByRole('button', { name: 'Details', exact: true }).click();
    await page.getByRole('button', { name: 'Review complaint', exact: true }).click();
    const decision = page.getByRole('dialog');
    await decision.getByRole('combobox', { name: 'Status', exact: false }).selectOption('upheld');
    await decision.getByLabel('Evidence reviewed and reason for decision').fill('Inspection confirmed that the repaired fitting still leaks.');
    await decision.getByRole('button', { name: 'Submit', exact: true }).click();
    await expect(decision).toHaveCount(0);
    await page.goto('/admin/dashboard');
    await expect(page.getByRole('heading', { name: 'Reliability evaluation from recorded outcomes' })).toBeVisible();
    await expect(page.getByText('eligible confirmed bookings', { exact: false })).toContainText('0');
    await expect(page.getByText('More genuine outcomes needed', { exact: true })).toBeVisible();
    const downloadEvent = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export real training outcomes', exact: true }).click();
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toContain('skillsync-real-outcomes-');
    expect(errors).toEqual([]);
});

test('public API data fits desktop and phone without demo content', async ({ page, request }) => {
    const workers = await request.get(backend + '/api/v1/workers');
    const records = (await workers.json()).data;
    const paths = ['/', '/services', '/workers', '/about', '/login', '/register'];
    if (records.length) paths.push('/workers/' + records[0].id);
    for (const width of [1440, 360]) {
        await page.setViewportSize({ width, height: 1000 });
        for (const path of paths) {
            expect((await page.goto(path)).status()).toBe(200);
            await expect(page.locator('h1').first()).toBeVisible();
            await expect(page.getByText('Demo mode', { exact: true })).toHaveCount(0);
            expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), path + ' overflow').toBe(true);
        }
    }
});

test('administrator inspects API records and records verification with a note', async ({ page, request }) => {
    await login(page, process.env.TEST_ADMIN_EMAIL, process.env.TEST_ADMIN_PASSWORD);
    await expect(page.locator('.ss-admin-dashboard')).toBeVisible();
    await page.screenshot({ path: '../../.integration-runtime/admin-dashboard-desktop.png', animations: 'disabled' });
    await page.setViewportSize({ width: 360, height: 900 });
    await page.goto('/admin/dashboard');
    await expect(page.locator('.ss-admin-dashboard')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await page.screenshot({ path: '../../.integration-runtime/admin-dashboard-mobile.png', animations: 'disabled' });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('/admin/records?entity=workers');
    const workerResponse = await request.get(backend + '/api/v1/workers');
    const worker = (await workerResponse.json()).data[0];
    expect(worker).toBeTruthy();
    await page.getByLabel('Search records').fill(worker.name);
    await page.locator('.fi-ta tbody tr').first().getByRole('button', { name: 'Details', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Profile details', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await page.getByRole('button', { name: 'Change requests', exact: true }).click();
    await page.getByRole('button', { name: 'Review changes', exact: true }).click();
    const dialog = page.getByRole('alertdialog');
    await dialog.getByLabel('Decision', { exact: false }).selectOption('approve');
    await dialog.getByLabel('Feedback for worker').fill('Profile checked during isolated integration testing.');
    await dialog.getByRole('button', { name: 'Save decision', exact: true }).click();
    await expect(dialog).toHaveCount(0);
    const verified = await request.get(backend + '/api/v1/workers/' + worker.id);
    expect((await verified.json()).data.verified).toBe(true);
    await page.getByRole('button', { name: 'Profile details', exact: true }).click();
    await page.getByRole('button', { name: 'Set data source', exact: true }).click();
    const source = page.getByRole('alertdialog');
    await source.getByLabel('Data source', { exact: false }).selectOption('real');
    await source.getByLabel('Verification evidence / reason').fill('Synthetic enrollment exercise in an isolated browser-test schema.');
    await source.getByRole('button', { name: 'Save data source', exact: true }).click();
    await expect(source).toHaveCount(0);
    const enrolled = await request.get(backend + '/api/v1/workers/' + worker.id);
    expect((await enrolled.json()).data.dataSource).toBe('real');
    await page.goto('/admin/records?entity=categories');
    await page.locator('.fi-ta tbody tr').filter({ hasText: 'Plumbing' }).getByRole('button', { name: 'Details', exact: true }).click();
    await page.getByRole('button', { name: 'Edit description', exact: true }).click();
    const categoryDialog = page.getByRole('dialog');
    await categoryDialog.getByLabel('Description', { exact: false }).fill('Plumbing repairs updated through the integrated admin panel.');
    await categoryDialog.getByRole('button', { name: 'Submit', exact: true }).click();
    await expect(categoryDialog).toHaveCount(0);
    await page.reload();
    await expect(page.getByText('Plumbing repairs updated through the integrated admin panel.').first()).toBeVisible();
});
