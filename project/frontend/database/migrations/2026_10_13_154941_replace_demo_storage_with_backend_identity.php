<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Only the retired frontend demo data is removed; PostgreSQL belongs to the API.
        DB::table('sessions')->delete();
        DB::table('users')->whereNotNull('demo_id')->delete();
        Schema::dropIfExists('demo_stores');
        Schema::table('users', function (Blueprint $table): void {
            $table->dropUnique(['demo_id']);
            $table->dropColumn('demo_id');
            $table->string('backend_id', 36)->nullable()->unique();
        });
    }

    public function down(): void
    {
        Schema::table('users', function (Blueprint $table): void {
            $table->dropUnique(['backend_id']);
            $table->dropColumn('backend_id');
            $table->string('demo_id')->nullable()->unique();
        });
        Schema::create('demo_stores', function (Blueprint $table): void {
            $table->string('id')->primary();
            $table->unsignedInteger('schema_version');
            $table->longText('payload');
            $table->timestamps();
        });
    }
};
