<?php

namespace Tests\Feature;

use App\Contracts\SkillSyncGateway;
use App\Filament\Admin\Pages\Records;
use App\Filament\Customer\Pages\NewRequest;
use App\Filament\Customer\Pages\Recommendations;
use App\Filament\Customer\Pages\RequestDetails;
use App\Livewire\Shared\NotificationBell;
use App\Livewire\Shared\Notifications;
use App\Models\User;
use App\Services\SkillSync\BackendClient;
use Filament\Facades\Filament;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\Http;
use Livewire\Livewire;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class ApiIntegrationTest extends TestCase
{
    use RefreshDatabase;

    private string $role = 'customer';

    private bool $modelAvailable = false;

    private bool $bookingConflict = false;

    private ?string $requestCategory = null;

    protected function setUp(): void
    {
        parent::setUp();
        $this->withoutVite();
        config(['skillsync.fastapi_base_url' => 'http://backend.test']);
        Http::preventStrayRequests();
        $this->fakeApi();
    }

    private function identity(): array
    {
        return ['id' => '11111111-1111-4111-8111-111111111111', 'name' => 'API Account',
            'email' => 'account@example.com', 'role' => $this->role, 'town' => 'Colombo',
            'workerId' => $this->role === 'worker' ? '22222222-2222-4222-8222-222222222222' : null,
            'phone' => '0771234567', 'contactPreference' => 'phone'];
    }

    private function worker(): array
    {
        return ['id' => '22222222-2222-4222-8222-222222222222', 'name' => 'API Professional',
            'town' => 'Colombo', 'serviceTowns' => ['Colombo'], 'categories' => ['Plumbing'],
            'bio' => 'Careful household plumbing repairs.', 'yearsExperience' => 5,
            'rateLkr' => 2500, 'rateUnit' => 'visit', 'available' => true,
            'rating' => null, 'reviewCount' => 0, 'verified' => false, 'reviews' => [],
            'reliabilityProbability' => $this->modelAvailable ? 0.84 : null,
            'coldStart' => true, 'imputedFeatures' => ['late_rate_before'],
            'missingScoringFeatures' => ['certified', 'distance_km'],
            'performance' => [['category' => 'Plumbing', 'completedJobs' => 0, 'skillScore' => $this->modelAvailable ? 76 : null]]];
    }

    private function job(): array
    {
        return ['id' => '33333333-3333-4333-8333-333333333333',
            'customerId' => $this->identity()['id'], 'title' => 'API kitchen tap repair',
            'description' => 'The kitchen tap leaks and needs a repair.', 'town' => 'Colombo',
            'address' => null, 'preferredAt' => now()->addDays(2)->toIso8601String(),
            'budgetLkr' => null, 'category' => $this->requestCategory, 'status' => 'submitted',
            'createdAt' => now()->toIso8601String()];
    }

    private function page(array $data): array
    {
        return ['data' => $data, 'meta' => ['page' => 1, 'perPage' => 100, 'total' => count($data), 'lastPage' => 1]];
    }

    private function stub(array|callable $callback): void
    {
        Http::swap(new Factory);
        Http::preventStrayRequests();
        Http::fake($callback);
    }

    private function fakeApi(): void
    {
        $this->stub(function (Request $request) {
            $path = parse_url($request->url(), PHP_URL_PATH);
            if ($path === '/api/v1/bookings' && $request->method() === 'POST' && $this->bookingConflict) {
                return Http::response(['error' => ['code' => 'booking_time_conflict',
                    'message' => 'This worker already has a booking during this time.',
                    'fields' => ['scheduledAt' => ['This worker already has a booking during this time.']]]], 409);
            }
            $identity = $this->identity();
            $worker = $this->worker();
            $job = $this->job();
            if ($path === '/api/v1/requests/'.$job['id'].'/classify') {
                if (! $this->modelAvailable) {
                    return Http::response(['error' => ['code' => 'model_unavailable', 'message' => 'The classification model is unavailable.']], 503);
                }
                $this->requestCategory = 'Plumbing';

                return Http::response(['data' => ['category' => 'Plumbing', 'source' => 'model', 'confidence' => null]]);
            }
            if ($request->method() === 'PATCH' && $path === '/api/v1/requests/'.$job['id'] && array_key_exists('category', $request->data())) {
                $this->requestCategory = $request['category'];
                $job = $this->job();
            }
            $category = ['id' => 'cat08', 'label' => 'Plumbing', 'slug' => 'plumbing',
                'icon' => 'heroicon-o-wrench-screwdriver', 'description' => 'Household plumbing repairs.',
                'exampleRequest' => 'Please repair my leaking kitchen tap.'];
            if (in_array($path, ['/api/v1/auth/login', '/api/v1/auth/register'])) {
                return Http::response(['data' => ['accessToken' => 'secret-api-token', 'tokenType' => 'bearer',
                    'expiresAt' => now()->addHours(8)->toIso8601String(), 'user' => $identity]], $path === '/api/v1/auth/register' ? 201 : 200);
            }
            $result = match ($path) {
                '/api/v1/auth/logout' => ['data' => ['message' => 'Signed out.']],
                '/api/v1/me' => ['data' => $identity],
                '/api/v1/categories' => ['data' => [$category]],
                '/api/v1/workers' => $this->page([$worker]),
                '/api/v1/workers/'.$worker['id'], '/api/v1/worker/profile' => ['data' => $worker],
                '/api/v1/worker/performance' => ['data' => ['performance' => $worker['performance'], 'completedJobs' => 0,
                    'rating' => null, 'reviewCount' => 0, 'reliabilityProbability' => $worker['reliabilityProbability'], 'modelStatus' => $this->modelAvailable ? 'available' : 'unavailable']],
                '/api/v1/requests' => $request->method() === 'POST' ? ['data' => $job] : $this->page([$job]),
                '/api/v1/requests/'.$job['id'] => ['data' => $job],
                '/api/v1/requests/'.$job['id'].'/recommendations' => ['data' => ['requestId' => $job['id'], 'category' => 'Plumbing', 'source' => $this->modelAvailable ? 'model' : 'rule_based',
                    'recommendations' => [['workerId' => $worker['id'], 'rank' => 1, 'matchScore' => $this->modelAvailable ? 80 : null,
                        'categorySkillScore' => $this->modelAvailable ? 76 : null, 'reliabilityProbability' => $worker['reliabilityProbability'], 'source' => $this->modelAvailable ? 'model' : 'rule_based',
                        'coldStart' => true, 'imputedFeatures' => ['late_rate_before'],
                        'missingScoringFeatures' => ['distance_km'],
                        'worker' => $worker, 'reasons' => ['Offers Plumbing in Colombo.']]]]],
                '/api/v1/bookings' => $request->method() === 'POST' ? ['data' => ['id' => 'saved-booking']] : $this->page([]),
                '/api/v1/notifications' => $this->page([]),
                '/api/v1/dashboard' => ['data' => ['role' => $this->role, 'requests' => 145, 'bookings' => 120,
                    'bookingsByStatus' => ['pending' => 20, 'completed' => 100], 'unreadNotifications' => 0]],
                '/api/v1/admin/dashboard' => ['data' => ['counts' => ['workers' => 121, 'customers' => 135, 'categories' => 4,
                    'requests' => 145, 'bookings' => 120, 'reviews' => 90], 'models' => ['classification' => $this->modelAvailable ? 'available' : 'unavailable', 'recommendations' => $this->modelAvailable ? 'model' : 'rule_based', 'performance' => $this->modelAvailable ? 'available' : 'unavailable']]],
                '/api/v1/admin/workers' => $this->page([$worker]),
                '/api/v1/admin/workers/'.$worker['id'].'/verification' => ['data' => $worker],
                '/api/v1/admin/customers' => $this->page([$identity]),
                '/api/v1/admin/categories' => $this->page([$category]),
                '/api/v1/admin/requests' => $this->page([$job]),
                '/api/v1/admin/bookings', '/api/v1/admin/reviews' => $this->page([]),
                default => null,
            };

            return $result === null
                ? Http::response(['error' => ['code' => 'not_found', 'message' => 'Not found.']], 404)
                : Http::response($result);
        });
    }

    private function login(string $role = 'customer'): User
    {
        $this->role = $role;
        $this->post('/login', ['email' => 'ACCOUNT@example.com', 'password' => 'PasswordForTest!'])
            ->assertRedirect('/'.$role.'/dashboard');

        return User::firstOrFail();
    }

    public function test_public_pages_display_api_records_without_demo_accounts_or_fixed_worker_ids(): void
    {
        foreach (['/', '/services', '/workers', '/about', '/login', '/register', '/workers/'.$this->worker()['id']] as $path) {
            $this->get($path)->assertOk()->assertDontSee('Demo mode')->assertDontSee('Arul Selvan');
        }
        $this->get('/')->assertSee('API Professional');
        $this->get('/workers/'.$this->worker()['id'])->assertSee('Not available yet')
            ->assertSee('Back to professionals')->assertSee('href="'.route('workers').'"', false);
        $this->get('/workers/missing')->assertNotFound();
        $this->post('/demo/login', ['role' => 'admin'])->assertStatus(405);
        $this->assertDatabaseCount('users', 0);
        Http::assertNotSent(fn (Request $request) => str_contains($request->url(), '/w01'));
    }

    public function test_login_encrypts_token_forwards_it_and_uses_backend_identity(): void
    {
        $user = $this->login();
        $this->assertAuthenticatedAs($user);
        $this->assertSame($this->identity()['id'], $user->backend_id);
        $this->assertNotSame('secret-api-token', session('backend_token'));
        $this->assertSame('secret-api-token', Crypt::decryptString(session('backend_token')));
        $this->get('/customer/dashboard')->assertOk()->assertDontSee('secret-api-token');
        $this->assertSame(145, app(SkillSyncGateway::class)->dashboard($user)['data']['requests']);
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/me') && $request->hasHeader('Authorization', 'Bearer secret-api-token'));
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/auth/login') && $request['email'] === 'account@example.com');
        $this->get('/worker/dashboard')->assertForbidden();
        $this->get('/admin/dashboard')->assertForbidden();
    }

    public function test_worker_registration_uses_api_accepts_normal_email_and_opens_profile(): void
    {
        $this->role = 'worker';
        $this->post('/register', ['name' => 'New Worker', 'email' => 'new@skillsync.test', 'role' => 'worker',
            'town' => 'Colombo', 'password' => 'PasswordForTest!', 'password_confirmation' => 'PasswordForTest!'])
            ->assertRedirect('/worker/profile');
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/auth/register')
            && $request['email'] === 'new@skillsync.test' && ! isset($request['password_confirmation']));
        $this->assertSame('worker', User::firstOrFail()->role);
    }

    public function test_public_registration_cannot_request_admin_role(): void
    {
        $this->post('/register', ['name' => 'Admin', 'email' => 'admin@example.com', 'role' => 'admin',
            'town' => 'Colombo', 'password' => 'PasswordForTest!', 'password_confirmation' => 'PasswordForTest!'])
            ->assertSessionHasErrors('role');
        Http::assertNothingSent();
        $this->assertGuest();
    }

    public function test_registration_errors_belong_to_town_and_password_confirmation(): void
    {
        foreach (['', 'DifferentPassword!'] as $confirmation) {
            $this->from('/register')->post('/register', [
                'name' => 'New Customer', 'email' => 'new@example.com', 'role' => 'customer',
                'town' => '', 'password' => 'PasswordForTest!', 'password_confirmation' => $confirmation,
            ])->assertRedirect('/register')
                ->assertSessionHasErrors(['town', 'password_confirmation'])
                ->assertSessionDoesntHaveErrors('password');

            $this->view('public.register', ['errors' => session('errors')])
                ->assertSee('aria-describedby="town-error"', false)
                ->assertSee('aria-describedby="password-confirmation-error"', false)
                ->assertSee($confirmation === '' ? 'Please confirm your password.' : 'The passwords do not match.')
                ->assertDontSee('PasswordForTest!');
        }
        Http::assertNothingSent();
        $this->assertGuest();
    }

    public function test_invalid_login_and_duplicate_registration_show_field_errors(): void
    {
        $this->stub(['*' => Http::response(['error' => ['message' => 'Invalid credentials.']], 401)]);
        $this->post('/login', ['email' => 'bad@example.com', 'password' => 'bad'])->assertSessionHasErrors('email');
        $this->assertGuest();
        $this->assertDatabaseCount('users', 0);
        $this->stub(['*' => Http::response(['error' => ['message' => 'An account already exists.']], 409)]);
        $this->post('/register', ['name' => 'Duplicate', 'email' => 'duplicate@example.com', 'role' => 'customer',
            'town' => 'Colombo', 'password' => 'PasswordForTest!', 'password_confirmation' => 'PasswordForTest!'])
            ->assertSessionHasErrors('email');
    }

    public function test_expired_token_clears_local_session_and_redirects_to_login(): void
    {
        $this->login();
        $this->stub(['*' => Http::response(['error' => ['message' => 'Expired.']], 401)]);
        $this->get('/customer/dashboard')->assertRedirect('/login');
        $this->assertGuest();
        $this->assertNull(session('backend_token'));
    }

    public function test_public_header_offers_post_logout_for_each_authenticated_role(): void
    {
        $this->get('/about')->assertOk()->assertSee('Log in')->assertDontSee('Logging out');
        foreach (['customer', 'worker', 'admin'] as $role) {
            $this->login($role);
            $response = $this->get('/about')->assertOk()->assertSee('Log out')->assertSee('My workspace')
                ->assertSeeHtml('class="ss-header-logout"')->assertSeeHtml('class="ss-mobile-logout"')
                ->assertSeeHtml('method="post" action="'.route('logout').'"');
            $this->assertSame(1, substr_count($response->getContent(), 'class="ss-header-logout"'));
            $this->assertSame(1, substr_count($response->getContent(), 'class="ss-mobile-logout"'));
            $this->post('/logout')->assertRedirect('/');
            $this->assertGuest();
        }
    }

    public function test_logout_revokes_token_and_clears_session(): void
    {
        $this->login();
        $this->post('/logout')->assertRedirect('/');
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/auth/logout')
            && $request->hasHeader('Authorization', 'Bearer secret-api-token'));
        $this->assertGuest();
        $this->assertNull(session('backend_token'));
    }

    public function test_panel_menu_logout_also_revokes_the_backend_token(): void
    {
        $this->login('worker');
        $this->post('/worker/logout')->assertRedirect('/');
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/auth/logout')
            && $request->hasHeader('Authorization', 'Bearer secret-api-token'));
        $this->assertGuest();
        $this->assertNull(session('backend_token'));
    }

    public function test_backend_failure_never_displays_fallback_profiles_and_logout_still_works(): void
    {
        $this->login();
        $this->stub(['*' => Http::failedConnection()]);
        $this->get('/customer/dashboard')->assertStatus(503);
        $this->post('/logout')->assertRedirect('/');
        $this->assertGuest();
        $this->get('/')->assertOk()->assertSee('temporarily unavailable')->assertDontSee('API Professional')->assertDontSee('Arul Selvan');
    }

    public function test_customer_pages_and_manual_category_flow_render(): void
    {
        $this->login();
        foreach (['/customer/requests/new', '/customer/requests/'.$this->job()['id'],
            '/customer/requests/'.$this->job()['id'].'/recommendations', '/customer/bookings',
            '/customer/profile', '/customer/notifications', '/customer/settings'] as $path) {
            $response = $this->get($path)->assertOk();
            if ($path === '/customer/requests/new') {
                $response->assertDontSee('Use current location')
                    ->assertSee('Search address')->assertSee('Use map centre')->assertSee('Clear location');
            }
        }
        Filament::setCurrentPanel(Filament::getPanel('customer'));
        Livewire::test(RequestDetails::class, ['requestId' => $this->job()['id']])
            ->call('findWorkers')->assertRedirect('/customer/requests/'.$this->job()['id'].'/recommendations');
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/classify'));
    }

    public function test_missing_category_uses_classifier_and_displays_real_model_ranking(): void
    {
        $this->modelAvailable = true;
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));

        Livewire::test(Recommendations::class, ['requestId' => $this->job()['id']])
            ->assertSet('category', 'Plumbing')
            ->assertSet('recommendationSource', 'model')
            ->assertSee('AI suggested Plumbing')
            ->assertSee('AI ranked matches')
            ->assertSee('Back to request')
            ->assertSeeHtml('href="/customer/requests/'.$this->job()['id'].'"')
            ->assertSee('Provisional estimate')
            ->assertSee('limited work history.')
            ->assertSee('80/100')
            ->assertDontSee('alphabetical order');
        Http::assertSent(fn (Request $request) => $request->method() === 'POST' && str_ends_with($request->url(), '/classify'));
    }

    public function test_recommendation_reasons_keep_three_visible_and_preserve_details_and_caveats(): void
    {
        $data = ['reasons' => ['Offers Plumbing', 'Serves Colombo', 'Available for new jobs',
            'No recorded reviews yet.', '<script>untrusted()</script>'],
            'matchScore' => 70, 'reliabilityProbability' => 0.6, 'coldStart' => true, 'dataSource' => 'demo'];
        $view = $this->blade('<x-recommendation-explanation :data="$data" :model="true" />', ['data' => $data])
            ->assertSee('Provisional estimate')->assertSee('Demo data')->assertSee('limited work history.')
            ->assertSee('More reasons and how this score works')
            ->assertSee('No recorded reviews yet.')->assertDontSee('<script>untrusted()</script>', false);
        $document = new \DOMDocument;
        @$document->loadHTML((string) $view);
        $xpath = new \DOMXPath($document);
        $this->assertSame(3, $xpath->query('//ul[contains(@class, "ss-reason-preview")]/li')->length);
        $this->assertSame(2, $xpath->query('//details//ul/li')->length);
        $this->assertSame(0, $xpath->query('//details[@open]')->length);
        $this->assertSame(0, $xpath->query('//details//*[contains(@class, "ss-estimate-note")]')->length);
        $data['coldStart'] = false;
        $data['reasons'] = [];
        $data['dataSource'] = 'real';
        $this->blade('<x-recommendation-explanation :data="$data" :model="true" />', ['data' => $data])
            ->assertDontSee('Provisional estimate')->assertDontSee('Demo data')
            ->assertSee('No recommendation reasons are available yet.');
    }

    public function test_classifier_outage_keeps_manual_category_and_rule_based_matching_available(): void
    {
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));

        Livewire::test(Recommendations::class, ['requestId' => $this->job()['id']])
            ->assertSet('category', '')
            ->assertSee('Automatic categorization is currently unavailable')
            ->set('category', 'Plumbing')
            ->assertSet('recommendationSource', 'rule_based')
            ->assertSee('API Professional')
            ->assertSee('alphabetical order')
            ->assertDontSee('AI ranked matches')
            ->assertDontSee('Provisional estimate')
            ->assertDontSee('Automatic categorization is currently unavailable');
        Http::assertSent(fn (Request $request) => $request->method() === 'PATCH' && $request['category'] === 'Plumbing');
    }

    public function test_existing_manual_category_is_never_overwritten_by_classifier(): void
    {
        $this->requestCategory = 'Plumbing';
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));

        Livewire::test(Recommendations::class, ['requestId' => $this->job()['id']])
            ->assertSet('category', 'Plumbing')
            ->assertSee('API Professional');
        Http::assertNotSent(fn (Request $request) => str_ends_with($request->url(), '/classify'));
    }

    public function test_customer_can_edit_request_and_clear_optional_fields(): void
    {
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));
        $job = [...$this->job(), 'category' => 'Plumbing', 'address' => 'Old address', 'budgetLkr' => 5000];
        $this->stub(function (Request $request) use (&$job) {
            if ($request->method() === 'PATCH') {
                $job = array_replace($job, $request->data());
            }
            $path = parse_url($request->url(), PHP_URL_PATH);

            return Http::response(['data' => match ($path) {
                '/api/v1/me' => $this->identity(),
                '/api/v1/categories' => [['label' => 'Plumbing']],
                default => $job,
            }]);
        });
        Livewire::test(RequestDetails::class, ['requestId' => $job['id']])
            ->mountAction('edit')->assertActionDataSet(['title' => $job['title'], 'address' => 'Old address'])
            ->setActionData(['title' => 'Repair bathroom pipes', 'description' => 'Replace the leaking bathroom water pipes.',
                'town' => 'Jaffna', 'address' => '', 'budgetLkr' => '',
                'preferredAt' => '2099-01-15 10:00:00', 'latitude' => 9.66, 'longitude' => 80.01])
            ->callMountedAction()->assertHasNoActionErrors()->assertSee('Repair bathroom pipes')->assertSee('Jaffna');
        Http::assertSent(fn (Request $request) => $request->method() === 'PATCH'
            && $request['preferredAt'] === '2099-01-15T10:00:00+05:30'
            && $request['address'] === null && $request['budgetLkr'] === null
            && ! array_key_exists('category', $request->data()) && $request['latitude'] == 9.66);
    }

    public function test_edit_request_rejects_invalid_inputs_without_saving(): void
    {
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));
        Livewire::test(RequestDetails::class, ['requestId' => $this->job()['id']])
            ->mountAction('edit')->setActionData(['title' => 'tiny', 'description' => 'short', 'budgetLkr' => -1,
                'preferredAt' => '2020-01-01 10:00:00'])
            ->callMountedAction()->assertHasActionErrors(['title', 'description', 'budgetLkr', 'preferredAt'])
            ->assertActionMounted('edit');
        Http::assertNotSent(fn (Request $request) => $request->method() === 'PATCH');
    }

    public function test_edit_request_shows_booking_conflict_and_hides_action_when_booked(): void
    {
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));
        $booked = false;
        $this->stub(function (Request $request) use (&$booked) {
            if ($request->method() === 'PATCH') {
                return Http::response(['error' => ['message' => 'Only an unbooked request can be edited.']], 409);
            }

            return Http::response(['data' => match (parse_url($request->url(), PHP_URL_PATH)) {
                '/api/v1/me' => $this->identity(),
                '/api/v1/categories' => [['label' => 'Plumbing']],
                default => [...$this->job(), 'status' => $booked ? 'booked' : 'submitted'],
            }]);
        });
        $component = Livewire::test(RequestDetails::class, ['requestId' => $this->job()['id']])
            ->mountAction('edit')->callMountedAction()->assertHasActionErrors(['operation'])
            ->assertActionMounted('edit');
        $this->assertStringContainsString('Only an unbooked request can be edited.', $component->instance()->getMountedAction()->getModalContent()->render());
        $booked = true;
        Livewire::test(RequestDetails::class, ['requestId' => $this->job()['id']])->assertActionHidden('edit');
    }

    public function test_booking_defaults_deadline_to_end_time_and_supports_custom_deadline(): void
    {
        $this->requestCategory = 'Plumbing';
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));
        foreach ([false, true] as $customDeadline) {
            $this->fakeApi();
            Livewire::test(Recommendations::class, ['requestId' => $this->job()['id']])
                ->mountAction('book', ['workerId' => $this->worker()['id']])
                ->assertActionDataSet(['customDeadline' => false])
                ->setActionData(['scheduledAt' => '2099-01-15 10:00:00',
                    'scheduledEndAt' => '2099-01-15 12:00:00', 'customDeadline' => true,
                    'deadlineAt' => '2099-01-15 18:00:00', 'confirmed' => true])
                ->setActionData(['customDeadline' => $customDeadline])
                ->callMountedAction()->assertHasNoActionErrors()
                ->assertRedirect('/customer/bookings/saved-booking');
            Http::assertSent(fn (Request $request) => $request->method() === 'POST'
                && str_ends_with($request->url(), '/bookings')
                && $request['deadlineAt'] === ($customDeadline ? '2099-01-15T18:00:00+05:30' : '2099-01-15T12:00:00+05:30')
                && ! array_key_exists('customDeadline', $request->data()));
        }
    }

    public function test_custom_booking_deadline_must_be_provided_and_not_before_end(): void
    {
        $this->requestCategory = 'Plumbing';
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));
        foreach ([null, '2099-01-15 11:00:00'] as $deadline) {
            Livewire::test(Recommendations::class, ['requestId' => $this->job()['id']])
                ->mountAction('book', ['workerId' => $this->worker()['id']])
                ->setActionData(['scheduledAt' => '2099-01-15 10:00:00',
                    'scheduledEndAt' => '2099-01-15 12:00:00', 'customDeadline' => true,
                    'deadlineAt' => $deadline, 'confirmed' => true])
                ->callMountedAction()->assertHasActionErrors(['deadlineAt'])->assertActionMounted('book');
        }
        Http::assertNotSent(fn (Request $request) => $request->method() === 'POST' && str_ends_with($request->url(), '/bookings'));
    }

    public function test_booking_time_conflict_is_shown_inside_booking_form(): void
    {
        $this->requestCategory = 'Plumbing';
        $this->bookingConflict = true;
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));
        Livewire::test(Recommendations::class, ['requestId' => $this->job()['id']])
            ->mountAction('book', ['workerId' => $this->worker()['id']])
            ->assertActionMounted('book')
            ->setActionData(['scheduledAt' => '2099-01-15 10:00:00',
                'scheduledEndAt' => '2099-01-15 12:00:00', 'deadlineAt' => '2099-01-15 18:00:00',
                'confirmed' => true])
            ->callMountedAction()
            ->assertHasActionErrors(['scheduledAt'])
            ->assertActionMounted('book');
        Http::assertSent(fn (Request $request) => $request->method() === 'POST'
            && str_ends_with($request->url(), '/bookings')
            && $request['scheduledEndAt'] === '2099-01-15T12:00:00+05:30');
    }

    public function test_worker_and_public_profile_describe_returned_predictions(): void
    {
        $this->modelAvailable = true;
        $this->login('worker');

        $this->get('/worker/performance')->assertOk()
            ->assertSee('Predicted on-time completion')
            ->assertSee('The model estimates the chance of completing work by the agreed deadline. Missing history uses typical training values.')
            ->assertDontSee('AI skill and reliability scores are not available yet.');
        $this->get('/workers/'.$this->worker()['id'])->assertOk()
            ->assertSee('Predicted on-time completion')
            ->assertSee('The model estimates the chance of completing work by the agreed deadline.')
            ->assertDontSee('AI reliability prediction is not available yet.');
    }

    public function test_worker_pages_merge_contact_and_performance_details(): void
    {
        $user = $this->login('worker');
        foreach (['/worker/dashboard', '/worker/jobs', '/worker/profile', '/worker/performance', '/worker/notifications', '/worker/settings'] as $path) {
            $this->get($path)->assertOk();
        }
        $profile = app(SkillSyncGateway::class)->profile($user)['data'];
        $this->assertSame('0771234567', $profile['phone']);
        $this->assertSame('phone', $profile['contactPreference']);
        $this->assertSame('API Professional', $profile['name']);
        $this->get('/customer/dashboard')->assertForbidden();
    }

    public function test_admin_pages_use_backend_counts_and_roles(): void
    {
        $this->login('admin');
        $this->get('/admin/dashboard')->assertOk()->assertSee('121')->assertSee('135');
        foreach (['workers', 'customers', 'categories', 'requests', 'bookings', 'reviews'] as $entity) {
            $this->get('/admin/records?entity='.$entity)->assertOk();
        }
        $this->get('/customer/dashboard')->assertForbidden();
        $this->get('/worker/dashboard')->assertForbidden();
        Filament::setCurrentPanel(Filament::getPanel('admin'));
        Livewire::test(Records::class, ['recordId' => $this->worker()['id']])
            ->set('search', 'API Professional')->assertSee('Back to records')
            ->assertDontSee('Search records')->assertDontSee('Ready for approval only')
            ->set('recordId', '')->assertDontSee('Back to records')
            ->assertSee('Search records')->assertSee('Ready for approval only')
            ->assertSet('entity', 'workers')->assertSet('search', 'API Professional')
            ->assertSet('pendingOnly', false);
    }

    public function test_worker_tabs_have_separate_review_buttons_and_submit_decisions(): void
    {
        $this->login('admin');
        Filament::setCurrentPanel(Filament::getPanel('admin'));
        foreach ([
            ['profile', 'verify', 'Review application', 'Review worker application', 'Review changes', 'approve'],
            ['changes', 'reviewChanges', 'Review changes', 'Review profile changes', 'Review application', 'changes'],
        ] as [$tab, $action, $label, $heading, $otherLabel, $decision]) {
            $component = Livewire::test(Records::class, ['recordId' => $this->worker()['id'], 'detailTab' => $tab])
                ->assertSee($label)->assertDontSee($otherLabel)
                ->mountAction($action, ['id' => $this->worker()['id']])
                ->assertActionMounted($action);
            $this->assertSame($heading, $component->instance()->getMountedAction()->getModalHeading());
            $component->setActionData(['decision' => $decision, 'note' => 'Reviewed worker profile details.'])
                ->callMountedAction()->assertHasNoActionErrors();
            Http::assertSent(fn (Request $request) => $request->method() === 'PATCH'
                && str_ends_with($request->url(), '/workers/'.$this->worker()['id'].'/verification')
                && $request['verified'] === ($decision === 'approve')
                && $request['note'] === 'Reviewed worker profile details.');
        }
    }

    public function test_admin_rejections_are_visible_inside_the_open_action_modal(): void
    {
        $this->login('admin');
        Filament::setCurrentPanel(Filament::getPanel('admin'));
        foreach ([
            ['dataSource', ['dataSource' => 'real', 'note' => 'Checked participant details.'], 'Demo identities cannot be promoted to real. Register a genuine account instead.'],
            ['verify', ['decision' => 'approve', 'note' => 'Checked profile details.'], 'The worker must complete their biography, services, towns, and rate before approval.'],
            ['reviewChanges', ['decision' => 'approve', 'note' => 'Checked profile updates.'], 'The worker must complete their biography, services, towns, and rate before approval.'],
        ] as [$action, $data, $message]) {
            $worker = [...$this->worker(), 'dataSource' => 'demo', 'reviewReady' => false,
                'bio' => '', 'categories' => [], 'serviceTowns' => [], 'rateLkr' => null];
            $this->stub(function (Request $request) use ($worker, $message) {
                if ($request->method() === 'PATCH') {
                    return Http::response(['error' => ['code' => 'conflict', 'message' => $message]], 409);
                }

                return Http::response(str_ends_with(parse_url($request->url(), PHP_URL_PATH), '/me')
                    ? ['data' => $this->identity()] : $this->page([$worker]));
            });
            $component = Livewire::test(Records::class, ['recordId' => $worker['id']])
                ->assertSee('Profile incomplete')->assertSee('Demo accounts cannot become Real or Test.')
                ->mountAction($action, ['id' => $worker['id']])
                ->setActionData($data)->callMountedAction()
                ->assertHasActionErrors(['operation'])->assertActionMounted($action);
            $modal = $component->instance()->getMountedAction()->getModalContent()->render();
            $this->assertStringContainsString('role="alert"', $modal);
            $this->assertStringContainsString($message, $modal);
        }
    }

    public function test_admin_source_update_shows_current_value_and_saves_real_for_test_account(): void
    {
        $this->login('admin');
        Filament::setCurrentPanel(Filament::getPanel('admin'));
        $source = 'test';
        $this->stub(function (Request $request) use (&$source) {
            if ($request->method() === 'PATCH') {
                $source = $request['dataSource'];
            }
            $worker = [...$this->worker(), 'dataSource' => $source, 'reviewReady' => true];

            return Http::response($request->method() === 'PATCH' ? ['data' => $worker]
                : (str_ends_with(parse_url($request->url(), PHP_URL_PATH), '/me')
                    ? ['data' => $this->identity()] : $this->page([$worker])));
        });
        Livewire::test(Records::class, ['recordId' => $this->worker()['id']])
            ->mountAction('dataSource', ['id' => $this->worker()['id']])
            ->assertActionDataSet(['dataSource' => 'test'])
            ->setActionData(['dataSource' => 'real', 'note' => 'Genuine participant identity confirmed.'])
            ->callMountedAction()->assertHasNoActionErrors()->assertSee('Real');
        $this->assertSame('real', $source);
        Http::assertSent(fn (Request $request) => $request->method() === 'PATCH'
            && str_ends_with($request->url(), '/admin/data-sources/workers/'.$this->worker()['id'])
            && $request['dataSource'] === 'real');
    }

    public function test_admin_action_backend_validation_targets_the_modal_field(): void
    {
        $this->login('admin');
        Filament::setCurrentPanel(Filament::getPanel('admin'));
        $this->stub(function (Request $request) {
            if ($request->method() === 'PATCH') {
                return Http::response(['error' => ['fields' => ['note' => ['More verification evidence is required.']]]], 422);
            }

            return Http::response(str_ends_with(parse_url($request->url(), PHP_URL_PATH), '/me')
                ? ['data' => $this->identity()] : $this->page([$this->worker()]));
        });
        Livewire::test(Records::class, ['recordId' => $this->worker()['id']])
            ->mountAction('verify', ['id' => $this->worker()['id']])
            ->setActionData(['decision' => 'approve', 'note' => 'Checked profile details.'])
            ->callMountedAction()->assertHasActionErrors(['note'])->assertActionMounted('verify');
    }

    public function test_gateway_normalizes_filters_and_sends_only_allowed_fields(): void
    {
        $user = $this->login();
        app(SkillSyncGateway::class)->recommendations($user, $this->job()['id'], ['available' => true, 'maxRate' => '', 'demoState' => 'normal']);
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/recommendations')
            && $request->data() === ['available' => true, 'maxRate' => null]);
        app(SkillSyncGateway::class)->createRequest($user, ['title' => 'Repair leaking tap',
            'description' => 'Repair the leaking kitchen tap.', 'town' => 'Colombo',
            'preferredAt' => '2099-01-15 10:00:00', 'budgetLkr' => '', 'category' => '', 'role' => 'admin']);
        Http::assertSent(fn (Request $request) => $request->method() === 'POST' && str_ends_with($request->url(), '/requests')
            && $request['preferredAt'] === '2099-01-15T10:00:00+05:30' && $request['budgetLkr'] === null && ! isset($request['role']));
    }

    public function test_pagination_includes_records_after_first_page(): void
    {
        $this->login();
        $this->stub(function (Request $request) {
            $page = (int) $request['page'];

            return Http::response(['data' => [['id' => 'record-'.$page]], 'meta' => ['page' => $page, 'lastPage' => 3, 'total' => 3, 'perPage' => 1]]);
        });
        $result = app(BackendClient::class)->all('/bookings');
        $this->assertSame(['record-1', 'record-2', 'record-3'], array_column($result['data'], 'id'));
    }

    public function test_booking_deadline_and_complaint_payloads_preserve_contract(): void
    {
        $user = $this->login();
        $this->stub(fn (Request $request) => Http::response(['data' => ['id' => 'record']]));
        $gateway = app(SkillSyncGateway::class);
        $gateway->createBooking($user, ['requestId' => 'request', 'workerId' => 'worker',
            'scheduledAt' => '2099-01-15 10:00:00', 'scheduledEndAt' => '2099-01-15 12:00:00', 'deadlineAt' => '2099-01-15 18:00:00', 'prediction' => 1]);
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/bookings')
            && $request['scheduledEndAt'] === '2099-01-15T12:00:00+05:30'
            && $request['deadlineAt'] === '2099-01-15T18:00:00+05:30'
            && $request['scheduledAt'] === '2099-01-15T10:00:00+05:30' && ! isset($request['prediction']));
        $gateway->submitComplaint($user, 'booking', ['reason' => 'The repair still leaks.', 'status' => 'upheld']);
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/booking/complaint')
            && $request->data() === ['reason' => 'The repair still leaks.']);
        $gateway->resolveComplaint($user, 'complaint', ['status' => 'upheld', 'resolution' => 'Inspected the faulty repair.', 'reviewedBy' => 'spoof']);
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/complaint/resolution')
            && $request->data() === ['status' => 'upheld', 'resolution' => 'Inspected the faulty repair.']);
    }

    public function test_livewire_request_maps_backend_validation_errors_to_form_fields(): void
    {
        $this->login();
        Filament::setCurrentPanel(Filament::getPanel('customer'));
        $component = Livewire::test(NewRequest::class);
        $this->stub(function (Request $request) {
            if ($request->method() === 'POST') {
                return Http::response(['error' => ['message' => 'Please check your input.',
                    'fields' => ['preferredAt' => ['Choose a future appointment.']]]], 422);
            }

            return Http::response(['data' => str_ends_with($request->url(), '/me')
                ? $this->identity() : [['label' => 'Plumbing']]]);
        });
        $component->fillForm(['title' => 'Repair kitchen tap', 'description' => 'The kitchen tap keeps leaking.',
            'town' => 'Colombo', 'preferredAt' => now()->addDays(2)->format('Y-m-d H:i:s')])
            ->call('save')->assertHasFormErrors(['preferredAt']);
    }

    public function test_guest_cannot_open_role_workspaces(): void
    {
        foreach (['/customer/dashboard', '/worker/dashboard', '/admin/dashboard', '/settings', '/notifications',
            '/customer/settings', '/customer/notifications', '/worker/settings', '/worker/notifications',
            '/admin/settings', '/admin/notifications'] as $path) {
            $this->get($path)->assertRedirect('/login');
        }
    }

    public static function workspaceRoles(): array
    {
        return [['customer'], ['worker'], ['admin']];
    }

    #[DataProvider('workspaceRoles')]
    public function test_account_pages_use_each_roles_workspace_and_keep_legacy_links(string $role): void
    {
        auth()->logout();
        $this->login($role);
        foreach (['notifications' => 'Notifications', 'settings' => 'Account settings'] as $slug => $heading) {
            $path = '/'.$role.'/'.$slug;
            $this->get('/'.$slug)->assertRedirect($path);
            $response = $this->get($path)->assertOk()->assertSee($heading)
                ->assertSee('fi-sidebar', false)->assertDontSee('aria-label="Main navigation"', false)
                ->assertSee('href="'.url('/'.$role.'/dashboard').'"', false)
                ->assertSee('href="'.url('/'.$role.'/notifications').'"', false)
                ->assertSee('href="'.url('/'.$role.'/settings').'"', false)
                ->assertSee('href="'.route('home').'"', false);
            $document = new \DOMDocument;
            @$document->loadHTML($response->getContent());
            $activeLinks = (new \DOMXPath($document))->query(
                '//li[contains(concat(" ", normalize-space(@class), " "), " fi-active ")]//a[@href="'.url($path).'"]'
            );
            $this->assertSame(1, $activeLinks->length, 'The current account page must be highlighted.');
            if ($slug === 'settings') {
                $response->assertSee('API Account')->assertSee('action="'.route('logout').'"', false);
                if ($role === 'admin') {
                    $response->assertDontSee('Edit profile');
                } else {
                    $response->assertSee('href="/'.$role.'/profile"', false);
                }
            }
        }
        foreach (array_diff(['customer', 'worker', 'admin'], [$role]) as $otherRole) {
            $this->get('/'.$otherRole.'/notifications')->assertForbidden();
            $this->get('/'.$otherRole.'/settings')->assertForbidden();
        }
    }

    public function test_admin_data_source_and_training_export_gateway_contract(): void
    {
        $user = $this->login('admin');
        $this->stub(fn (Request $request) => Http::response(['data' => ['rows' => []]]));
        $gateway = app(SkillSyncGateway::class);
        $gateway->updateDataSource($user, 'workers', 'worker-id', ['dataSource' => 'real', 'note' => 'Verified genuine participant.', 'role' => 'admin']);
        Http::assertSent(fn (Request $request) => str_ends_with($request->url(), '/admin/data-sources/workers/worker-id')
            && $request->data() === ['dataSource' => 'real', 'note' => 'Verified genuine participant.']);
        $this->assertSame([], $gateway->trainingDataset($user)['data']['rows']);
        Http::assertSent(fn (Request $request) => $request->method() === 'GET' && str_ends_with($request->url(), '/admin/training-dataset'));
    }

    public function test_notification_count_uses_authenticated_unread_total_instead_of_page_length(): void
    {
        $user = $this->login();
        $this->stub(fn (Request $request) => Http::response([
            'data' => [['id' => 'notice', 'readAt' => null]],
            'meta' => ['page' => 1, 'perPage' => 1, 'total' => 125, 'lastPage' => 125],
        ]));

        $this->assertSame(125, app(SkillSyncGateway::class)->unreadNotificationCount($user));
        Http::assertSentCount(1);
        Http::assertSent(fn (Request $request) => $request->hasHeader('Authorization', 'Bearer secret-api-token')
            && $request['unread'] === 'true' && $request['perPage'] === 1 && ! isset($request['userId']));
    }

    public function test_notification_bell_refreshes_and_hides_zero_for_each_account_role(): void
    {
        foreach (['admin', 'worker', 'customer'] as $role) {
            auth()->logout();
            $this->fakeApi();
            $this->login($role);
            $count = 125;
            $this->stub(function (Request $request) use (&$count) {
                return Http::response(['data' => [], 'meta' => ['total' => $count]]);
            });
            $bell = Livewire::test(NotificationBell::class)
                ->assertSet('unreadCount', 125)->assertSee('99+')
                ->assertSee('Notifications, 125 unread');
            $count = 6;
            $bell->call('refreshCount')->assertSet('unreadCount', 6)->assertSee('Notifications, 6 unread');
            $count = 0;
            $bell->dispatch('notifications-updated')->assertSet('unreadCount', 0)
                ->assertDontSeeHtml('class="ss-notification-count"');
        }
    }

    public function test_notification_count_failure_does_not_break_navigation_or_show_a_false_zero(): void
    {
        $this->login();
        $this->stub(fn (Request $request) => Http::response(['data' => [], 'meta' => ['total' => 6]]));
        $bell = Livewire::test(NotificationBell::class)->assertSet('unreadCount', 6);
        $this->stub(fn (Request $request) => Http::response([], 503));
        $bell->call('refreshCount')->assertSet('unreadCount', null)
            ->assertSee('unread count unavailable')->assertDontSeeHtml('class="ss-notification-count"');
        $this->stub(fn (Request $request) => Http::response(['data' => [], 'meta' => ['total' => -1]]));
        $bell->call('refreshCount')->assertSet('unreadCount', null);
    }

    public function test_marking_a_notification_read_refreshes_the_bell(): void
    {
        $this->login();
        $notice = ['id' => 'notice', 'message' => 'Booking updated', 'targetPath' => '/customer/bookings',
            'createdAt' => now()->toIso8601String(), 'readAt' => null];
        $this->stub(function (Request $request) use (&$notice) {
            if ($request->method() === 'PATCH') {
                $notice['readAt'] = now()->toIso8601String();

                return Http::response(['data' => $notice]);
            }

            return Http::response($this->page([$notice]));
        });
        Livewire::test(Notifications::class)
            ->assertSeeHtml('class="ss-notification is-unread"')
            ->assertSeeHtml('<span class="sr-only">Unread notification</span>')
            ->call('markRead', 'notice')->assertDispatched('notifications-updated')
            ->assertDontSeeHtml('class="ss-notification is-unread"')
            ->assertDontSeeHtml('<span class="sr-only">Unread notification</span>')
            ->assertSeeHtml('class="ss-notification-read"');
        Http::assertSent(fn (Request $request) => $request->method() === 'PATCH'
            && str_ends_with($request->url(), '/notifications/notice') && $request['read'] === true);
    }

    public function test_opening_notification_marks_read_and_repeated_click_keeps_unread_count_zero(): void
    {
        $this->login();
        $notice = ['id' => 'notice', 'message' => 'Booking updated', 'targetPath' => '/customer/bookings/job-1',
            'createdAt' => now()->toIso8601String(), 'readAt' => null];
        $this->stub(function (Request $request) use (&$notice) {
            if ($request->method() === 'PATCH') {
                $notice['readAt'] ??= now()->toIso8601String();

                return Http::response(['data' => $notice]);
            }
            if (($request['unread'] ?? null) === 'true') {
                return Http::response(['data' => [], 'meta' => ['total' => $notice['readAt'] ? 0 : 1]]);
            }

            return Http::response($this->page([$notice]));
        });
        $list = Livewire::test(Notifications::class)->assertSee('Booking updated');
        Http::assertNotSent(fn (Request $request) => $request->method() === 'PATCH');
        $bell = Livewire::test(NotificationBell::class)->assertSet('unreadCount', 1);
        $list->call('openNotification', 'notice')->assertDispatched('notifications-updated')
            ->assertRedirect('/customer/bookings/job-1');
        $readAt = $notice['readAt'];
        $this->assertNotNull($readAt);
        $bell->dispatch('notifications-updated')->assertSet('unreadCount', 0);
        Livewire::test(Notifications::class)->assertSee('Read')->assertDontSee('Mark read')
            ->call('openNotification', 'notice')->assertRedirect('/customer/bookings/job-1');
        $this->assertSame($readAt, $notice['readAt']);
        $bell->dispatch('notifications-updated')->assertSet('unreadCount', 0);
        Http::assertSent(fn (Request $request) => $request->method() === 'PATCH'
            && str_ends_with($request->url(), '/notifications/notice') && $request['read'] === true);
    }

    public function test_notification_read_failure_does_not_redirect_or_report_success(): void
    {
        $this->login();
        $this->stub(fn (Request $request) => $request->method() === 'PATCH'
            ? Http::response([], 503) : Http::response($this->page([])));
        Livewire::test(Notifications::class)->call('openNotification', 'notice')
            ->assertNoRedirect()->assertNotDispatched('notifications-updated')
            ->assertSee('Could not mark this notification as read. Please try again.');
    }

    public function test_notification_open_requires_ownership_and_rejects_external_redirects(): void
    {
        $this->login();
        $this->stub(fn (Request $request) => $request->method() === 'PATCH'
            ? Http::response([], 404) : Http::response($this->page([])));
        Livewire::test(Notifications::class)->call('openNotification', 'someone-elses-notice')->assertStatus(404);
        $this->stub(fn (Request $request) => Http::response($request->method() === 'PATCH'
            ? ['data' => ['id' => 'notice', 'targetPath' => '//external.test', 'readAt' => now()->toIso8601String()]]
            : $this->page([])));
        Livewire::test(Notifications::class)->call('openNotification', 'notice')->assertRedirect('/notifications');
    }

    public function test_gps_coordinates_are_forwarded_and_can_be_cleared_without_accepting_client_distance(): void
    {
        $user = $this->login();
        $gateway = app(SkillSyncGateway::class);
        $gateway->createRequest($user, [
            'title' => 'Repair kitchen tap', 'description' => 'The kitchen tap keeps leaking.',
            'town' => 'Colombo', 'preferredAt' => now()->addDays(2)->toIso8601String(),
            'latitude' => 0, 'longitude' => 80, 'distanceKm' => 0,
        ]);
        Http::assertSent(fn (Request $request) => $request->method() === 'POST'
            && str_ends_with($request->url(), '/requests') && $request['latitude'] === 0
            && $request['longitude'] === 80 && ! isset($request['distanceKm']));
        $gateway->updateRequest($user, $this->job()['id'], ['latitude' => '', 'longitude' => '']);
        Http::assertSent(fn (Request $request) => $request->method() === 'PATCH'
            && array_key_exists('latitude', $request->data()) && $request['latitude'] === null
            && array_key_exists('longitude', $request->data()) && $request['longitude'] === null);
    }
}
