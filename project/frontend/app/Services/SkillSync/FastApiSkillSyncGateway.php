<?php

namespace App\Services\SkillSync;

use App\Contracts\SkillSyncGateway;
use App\Models\User;
use Carbon\Carbon;
use Illuminate\Support\Arr;
use Symfony\Component\HttpKernel\Exception\HttpException;

final class FastApiSkillSyncGateway implements SkillSyncGateway
{
    public function __construct(private BackendClient $api) {}

    private function id(string $id): string
    {
        return rawurlencode($id);
    }

    private function input(array $input, array $allowed, array $dates = []): array
    {
        $input = Arr::only($input, $allowed);
        foreach ($dates as $key) {
            if (! empty($input[$key])) {
                $input[$key] = Carbon::parse($input[$key], config('app.timezone'))->toIso8601String();
            }
        }
        foreach (['budgetLkr', 'maxRate', 'category', 'phone', 'address', 'latitude', 'longitude', 'serviceRadiusKm'] as $key) {
            if (array_key_exists($key, $input) && $input[$key] === '') {
                $input[$key] = null;
            }
        }
        foreach (['yearsExperience', 'rating'] as $key) {
            if (isset($input[$key]) && is_numeric($input[$key])) {
                $input[$key] = (int) $input[$key];
            }
        }

        return $input;
    }

    public function categories(): array
    {
        return $this->api->send('GET', '/categories', authenticated: false);
    }

    public function workers(array $filters = [], int $page = 1, int $perPage = 9): array
    {
        $filters = array_filter(Arr::only($filters, ['search', 'category', 'town', 'available', 'maxRate']), fn ($value) => $value !== '' && $value !== null);
        if (isset($filters['available'])) {
            $filters['available'] = $filters['available'] ? 'true' : 'false';
        }

        return $this->api->send('GET', '/workers', [...$filters, 'page' => $page, 'perPage' => $perPage], false);
    }

    public function worker(string $id): array
    {
        return $this->api->send('GET', '/workers/'.$this->id($id), authenticated: false);
    }

    public function requests(User $user): array
    {
        return $this->api->all('/requests');
    }

    public function request(User $user, string $id): array
    {
        return $this->api->send('GET', '/requests/'.$this->id($id));
    }

    public function createRequest(User $user, array $input): array
    {
        return $this->api->send('POST', '/requests', $this->input($input, ['title', 'description', 'town', 'address', 'preferredAt', 'budgetLkr', 'category', 'latitude', 'longitude'], ['preferredAt']));
    }

    public function classifyRequest(User $user, string $id): array
    {
        return $this->api->send('POST', '/requests/'.$this->id($id).'/classify');
    }

    public function updateRequest(User $user, string $id, array $input): array
    {
        return $this->api->send('PATCH', '/requests/'.$this->id($id), $this->input($input, ['title', 'description', 'town', 'address', 'preferredAt', 'budgetLkr', 'category', 'latitude', 'longitude'], ['preferredAt']));
    }

    public function recommendations(User $user, string $id, array $filters = []): array
    {
        return $this->api->send('POST', '/requests/'.$this->id($id).'/recommendations', $this->input($filters, ['available', 'maxRate']));
    }

    public function bookings(User $user, array $filters = []): array
    {
        $result = $this->api->all('/bookings');
        if (! empty($filters['status'])) {
            $result['data'] = array_values(array_filter($result['data'], fn ($record) => $record['status'] === $filters['status']));
        }

        return $result;
    }

    public function booking(User $user, string $id): array
    {
        return $this->api->send('GET', '/bookings/'.$this->id($id));
    }

    public function createBooking(User $user, array $input): array
    {
        return $this->api->send('POST', '/bookings', $this->input($input, ['requestId', 'workerId', 'scheduledAt', 'scheduledEndAt', 'deadlineAt'], ['scheduledAt', 'scheduledEndAt', 'deadlineAt']));
    }

    public function transitionBooking(User $user, string $id, string $status, ?string $note = null): array
    {
        return $this->api->send('PATCH', '/bookings/'.$this->id($id).'/status', compact('status', 'note'));
    }

    public function reviewBooking(User $user, string $id, array $input): array
    {
        return $this->api->send('POST', '/bookings/'.$this->id($id).'/review', $this->input($input, ['rating', 'comment']));
    }

    public function notifications(User $user): array
    {
        return $this->api->all('/notifications');
    }

    public function markNotificationRead(User $user, string $id): array
    {
        return $this->api->send('PATCH', '/notifications/'.$this->id($id), ['read' => true]);
    }

    public function unreadNotificationCount(User $user): int
    {
        $result = $this->api->send('GET', '/notifications', ['unread' => 'true', 'page' => 1, 'perPage' => 1]);
        $count = $result['meta']['total'] ?? null;
        if (! is_int($count) || $count < 0) {
            throw new HttpException(503, 'The service returned an invalid notification count.');
        }

        return $count;
    }

    public function profile(User $user): array
    {
        $result = $this->api->send('GET', '/me');
        if ($user->role === 'worker') {
            $result['data'] = [...$result['data'], ...$this->api->send('GET', '/worker/profile')['data']];
        }

        return $result;
    }

    public function updateProfile(User $user, array $input): array
    {
        $allowed = ['name', 'town', 'phone', 'contactPreference'];
        if ($user->role === 'worker') {
            $allowed = [...$allowed, 'bio', 'categories', 'serviceTowns', 'yearsExperience', 'rateLkr', 'rateUnit', 'available', 'latitude', 'longitude', 'serviceRadiusKm'];
        }
        $this->api->send('PATCH', $user->role === 'worker' ? '/worker/profile' : '/me', $this->input($input, $allowed));
        app(BackendIdentity::class)->sync($this->api->send('GET', '/me')['data'], $user);

        return $this->profile($user);
    }

    public function performance(User $user): array
    {
        $result = $this->api->send('GET', '/worker/performance');
        $result['data']['worker'] = $this->api->send('GET', '/worker/profile')['data'];
        $result['data']['bookings'] = $this->bookings($user, ['status' => 'completed'])['data'];

        return $result;
    }

    public function adminRecords(User $user, string $entity): array
    {
        return $this->api->all('/admin/'.$this->id($entity));
    }

    public function updateCategory(User $user, string $id, array $input): array
    {
        return $this->api->send('PATCH', '/admin/categories/'.$this->id($id), Arr::only($input, ['description', 'exampleRequest']));
    }

    public function verifyWorker(User $user, string $id, bool $verified, string $note): array
    {
        return $this->api->send('PATCH', '/admin/workers/'.$this->id($id).'/verification', compact('verified', 'note'));
    }

    public function dashboard(User $user): array
    {
        return $this->api->send('GET', $user->role === 'admin' ? '/admin/dashboard' : '/dashboard');
    }

    public function updateDataSource(User $user, string $entity, string $id, array $input): array
    {
        return $this->api->send('PATCH', '/admin/data-sources/'.$this->id($entity).'/'.$this->id($id), Arr::only($input, ['dataSource', 'note']));
    }

    public function trainingDataset(User $user): array
    {
        return $this->api->send('GET', '/admin/training-dataset');
    }

    public function submitComplaint(User $user, string $id, array $input): array
    {
        return $this->api->send('POST', '/bookings/'.$this->id($id).'/complaint', Arr::only($input, ['reason']));
    }

    public function resolveComplaint(User $user, string $id, array $input): array
    {
        return $this->api->send('PATCH', '/admin/complaints/'.$this->id($id).'/resolution', Arr::only($input, ['status', 'resolution']));
    }
}
