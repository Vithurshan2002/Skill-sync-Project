<?php

namespace App\Contracts;

use App\Models\User;

/**
 * Every result follows {data, meta?}. Lists are data arrays; workers includes
 * meta {page, perPage, total, lastPage}. Entity keys are camelCase, dates ISO8601.
 * Business validation raises ValidationException; access checks raise 403;
 * missing entities raise 404. Business data is provided by the backend API.
 */
interface SkillSyncGateway
{
    public function categories(): array;

    public function workers(array $filters = [], int $page = 1, int $perPage = 9): array;

    public function worker(string $id): array;

    public function requests(User $user): array;

    public function request(User $user, string $id): array;

    public function createRequest(User $user, array $input): array;

    public function classifyRequest(User $user, string $id): array;

    public function updateRequest(User $user, string $id, array $input): array;

    public function recommendations(User $user, string $id, array $filters = []): array;

    public function bookings(User $user, array $filters = []): array;

    public function booking(User $user, string $id): array;

    public function createBooking(User $user, array $input): array;

    public function transitionBooking(User $user, string $id, string $status, ?string $note = null): array;

    public function reviewBooking(User $user, string $id, array $input): array;

    public function notifications(User $user): array;

    public function unreadNotificationCount(User $user): int;

    public function markNotificationRead(User $user, string $id): array;

    public function profile(User $user): array;

    public function updateProfile(User $user, array $input): array;

    public function performance(User $user): array;

    public function adminRecords(User $user, string $entity): array;

    public function updateCategory(User $user, string $id, array $input): array;

    public function verifyWorker(User $user, string $id, bool $verified, string $note): array;

    public function submitComplaint(User $user, string $id, array $input): array;

    public function resolveComplaint(User $user, string $id, array $input): array;

    public function dashboard(User $user): array;

    public function updateDataSource(User $user, string $entity, string $id, array $input): array;

    public function trainingDataset(User $user): array;
}
