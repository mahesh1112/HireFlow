"use client";
import { useEffect, useState } from "react";
import { Building2, CheckCircle, Save } from "lucide-react";
import { Header } from "@/components/layouts/Header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { unitsApi } from "@/lib/api/units";
import type { BusinessUnit } from "@/lib/types";
import toast from "react-hot-toast";

export default function SettingsPage() {
  const [allUnits, setAllUnits] = useState<BusinessUnit[]>([]);
  const [myUnitIds, setMyUnitIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([unitsApi.listUnits(), unitsApi.getMyUnits()])
      .then(([all, mine]) => {
        setAllUnits(all);
        setMyUnitIds(new Set(mine.map((u) => u.id)));
      })
      .finally(() => setLoading(false));
  }, []);

  const toggleUnit = (unitId: string) => {
    setMyUnitIds((prev) => {
      const next = new Set(prev);
      if (next.has(unitId)) {
        next.delete(unitId);
      } else {
        next.add(unitId);
      }
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await unitsApi.assignMyUnits(Array.from(myUnitIds));
      toast.success("Unit assignments saved");
    } catch {
      toast.error("Failed to save unit assignments");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header
        title="Settings"
        subtitle="Manage your business unit memberships"
      />

      <div className="flex-1 p-8 max-w-2xl mx-auto w-full space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-500" />
              Business Unit Membership
            </CardTitle>
            <CardDescription>
              Select the business units you belong to. You will only see resumes
              from units you are assigned to, and can only upload resumes to
              those units.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-8">
                <div className="spinner w-6 h-6" />
              </div>
            ) : (
              <div className="space-y-3">
                {allUnits.map((unit) => {
                  const isSelected = myUnitIds.has(unit.id);
                  return (
                    <label
                      key={unit.id}
                      className={`flex items-center gap-4 p-4 rounded-xl border-2 cursor-pointer transition-colors ${
                        isSelected
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleUnit(unit.id)}
                        className="w-4 h-4 text-blue-600 rounded border-gray-300"
                      />
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{unit.unit_name}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          Slug: {unit.unit_slug}
                        </p>
                      </div>
                      {isSelected && (
                        <CheckCircle className="w-5 h-5 text-blue-500 flex-shrink-0" />
                      )}
                    </label>
                  );
                })}

                <div className="pt-4 flex justify-end">
                  <Button
                    onClick={handleSave}
                    isLoading={saving}
                    disabled={saving}
                    className="min-w-24"
                  >
                    <Save className="w-4 h-4" />
                    Save
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
